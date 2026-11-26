"""PRIME core application bootstrap, wiring, and graceful lifecycle management."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from prime.config.settings import (
    ActivationConfig,
    HardwareAIConfig,
    LanguageMode,
    MemoryProfile,
    PrimeConfig,
    load_config,
    save_config_toml,
)
from prime.core.events import AssistantState, EventBus
from prime.intelligence.context.assembler import ContextAssembler
from prime.intelligence.generation.service import GenerationConfig
from prime.intelligence.memory.store import MemoryStore
from prime.intelligence.models.registry import ModelRegistry
from prime.intelligence.providers.base import LLMProvider, StreamChunk
from prime.intelligence.providers.mlx_provider import MLXProvider
from prime.intelligence.runtime.manager import (
    LocalAIRuntime,
    RuntimeSnapshot,
    RuntimeState,
    default_budget_for_profile,
)
from prime.logging.logger import configure_logging, log_event
from prime.plugins.contracts import PluginRegistry
from prime.security.manager import SecurityManager
from prime.security.tiers import ConfirmationHandler
from prime.system.base import PlatformKind, SystemController
from prime.system.factory import create_system_controller
from prime.voice.contracts import ActivationSnapshot, ActivationStatus


@dataclass(frozen=True, slots=True)
class PrimeStatusSnapshot:
    app_name: str
    bundle_id: str
    version: str
    state: AssistantState
    platform: PlatformKind
    schema_version: int
    fts5_enabled: bool
    memory_profile: str
    language_mode: str
    local_only: bool


@dataclass(frozen=True, slots=True)
class TextSubmitResult:
    """Result of submitting a text prompt to PRIME without fabricating AI replies."""

    accepted: bool
    user_text: str
    backend_connected: bool
    system_notice: str
    conversation_id: int | None = None
    assistant_text: str = ""
    tokens_generated: int = 0
    tokens_per_sec: float = 0.0
    cancelled: bool = False


class PrimeApp:
    """Coordinates PRIME core modules with clean bootstrap and shutdown."""

    def __init__(
        self,
        config: PrimeConfig,
        *,
        confirmation_handler: ConfirmationHandler | None = None,
        llm_provider: LLMProvider | None = None,
        model_registry: ModelRegistry | None = None,
        console_logging: bool = False,
        platform_override: str | None = None,
    ) -> None:
        self.config = config
        self.state = AssistantState.STOPPED
        self.events = EventBus()
        self.logger: logging.Logger = configure_logging(
            config.logging, config.storage.log_dir, console=console_logging
        )
        self.security = SecurityManager(
            config.security,
            confirmation_handler=confirmation_handler,
            logger=self.logger.getChild("security"),
        )
        self.system: SystemController = create_system_controller(
            config,
            self.security,
            logger=self.logger.getChild("system"),
            platform_name=platform_override,
        )
        self.memory = MemoryStore(config.storage.db_path)
        self.context = ContextAssembler(
            self.memory,
            language_mode=config.ai.language_mode,
        )
        self.plugins = PluginRegistry(config.security)
        self._model_registry = model_registry or ModelRegistry(config.storage.models_dir)
        self._llm_provider: LLMProvider = llm_provider or MLXProvider()
        self.runtime = LocalAIRuntime(
            self._model_registry,
            self._llm_provider,
            generation_config=GenerationConfig(
                memory_budget_mb=config.ai.memory_budget_mb,
                max_context_tokens=config.ai.max_context_tokens,
                max_generation_tokens=config.ai.max_generation_tokens,
            ),
            selected_model_slug=config.ai.selected_model_slug,
            logger=self.logger.getChild("runtime"),
        )
        self.runtime.subscribe(
            lambda snap: self.events.publish(
                "ai.runtime_changed",
                {
                    "state": snap.state.value,
                    "active_model": snap.active_model_name,
                    "tps": snap.tokens_per_sec,
                    "tokens": snap.last_token_count,
                },
            )
        )
        self._active_conversation_id: int | None = None
        self._push_to_talk_pressed = False
        self._schema_version = 0

    @property
    def ai_backend_connected(self) -> bool:
        return self.runtime.is_ready

    @property
    def model_registry(self) -> ModelRegistry:
        return self._model_registry

    @property
    def active_conversation_id(self) -> int | None:
        return self._active_conversation_id

    def get_runtime_snapshot(self) -> RuntimeSnapshot:
        return self.runtime.snapshot()

    def load_local_model(self, slug: str | None = None) -> RuntimeSnapshot:
        if self.state == AssistantState.STOPPED:
            raise RuntimeError("PrimeApp must be bootstrapped before loading a local model.")
        return self.runtime.load_model(slug or self.config.ai.selected_model_slug)

    def unload_local_model(self) -> RuntimeSnapshot:
        return self.runtime.unload_model()

    def cancel_generation(self) -> RuntimeSnapshot:
        return self.runtime.cancel_generation()

    def get_activation_snapshot(self) -> ActivationSnapshot:
        ptt_status = (
            ActivationStatus.ACTIVE
            if self._push_to_talk_pressed
            else (
                ActivationStatus.CONFIGURED_UNAVAILABLE
                if self.config.activation.push_to_talk_enabled
                else ActivationStatus.DISABLED
            )
        )
        clap_status = (
            ActivationStatus.CONFIGURED_UNAVAILABLE
            if self.config.activation.double_clap_enabled
            else ActivationStatus.DISABLED
        )
        return ActivationSnapshot(
            push_to_talk_pressed=self._push_to_talk_pressed,
            push_to_talk_status=ptt_status,
            double_clap_enabled=self.config.activation.double_clap_enabled,
            double_clap_status=clap_status,
            microphone_permission_requested=False,
        )

    def set_push_to_talk(self, pressed: bool) -> ActivationSnapshot:
        """Toggle UI push-to-talk state without opening microphone hardware in Phase 03."""
        if self.state == AssistantState.STOPPED:
            raise RuntimeError("PrimeApp must be bootstrapped before changing activation state.")
        if not self.config.activation.push_to_talk_enabled:
            self._push_to_talk_pressed = False
            snap = self.get_activation_snapshot()
            self.events.publish("activation.changed", {"push_to_talk_pressed": False})
            return snap

        self._push_to_talk_pressed = bool(pressed)
        self._set_state(
            AssistantState.LISTENING if self._push_to_talk_pressed else AssistantState.IDLE
        )
        snap = self.get_activation_snapshot()
        self.events.publish(
            "activation.changed",
            {
                "push_to_talk_pressed": snap.push_to_talk_pressed,
                "push_to_talk_status": snap.push_to_talk_status.value,
            },
        )
        return snap

    def submit_text_message(
        self,
        text: str,
        *,
        on_token: Callable[[str, StreamChunk], None] | None = None,
    ) -> TextSubmitResult:
        """Process a user message locally; stream from MLX if loaded or report unavailability."""
        if self.state == AssistantState.STOPPED:
            raise RuntimeError("PrimeApp must be bootstrapped before submitting messages.")

        cleaned = text.strip()
        if not cleaned:
            return TextSubmitResult(
                accepted=False,
                user_text="",
                backend_connected=self.ai_backend_connected,
                system_notice="Message cannot be empty.",
                conversation_id=self._active_conversation_id,
            )

        if self._active_conversation_id is None:
            conv = self.memory.create_conversation("Desktop Session")
            self._active_conversation_id = conv.id

        # Assemble bounded multi-turn context BEFORE inserting the new user message
        # so the current user prompt appears once at the end of the prompt sequence.
        messages = self.context.build_messages(self._active_conversation_id, cleaned)

        self.memory.add_message(
            self._active_conversation_id,
            "user",
            cleaned,
            language=self.config.ai.language_mode.value,
        )
        self._set_state(AssistantState.THINKING)
        self.events.publish(
            "conversation.user_message", {"conversation_id": self._active_conversation_id}
        )

        if not self.ai_backend_connected:
            snap = self.runtime.snapshot()
            if snap.state == RuntimeState.MODEL_AVAILABLE:
                notice = (
                    f"Model '{snap.active_model_name}' is available locally but not loaded yet. "
                    "Click 'Load Model' to start local inference."
                )
            else:
                notice = (
                    "No local AI model is installed or loaded. "
                    "Your message was saved locally; no response was fabricated."
                )
            self._set_state(AssistantState.IDLE)
            self.events.publish("conversation.backend_unavailable", {"notice": notice})
            return TextSubmitResult(
                accepted=True,
                user_text=cleaned,
                backend_connected=False,
                system_notice=notice,
                conversation_id=self._active_conversation_id,
            )

        try:
            response = self.runtime.generate_stream(messages, on_token=on_token)
        except Exception as exc:
            self._set_state(AssistantState.IDLE)
            err_notice = f"Local generation failed: {exc}"
            self.events.publish("conversation.generation_error", {"error": err_notice})
            return TextSubmitResult(
                accepted=True,
                user_text=cleaned,
                backend_connected=False,
                system_notice=err_notice,
                conversation_id=self._active_conversation_id,
            )

        if response.text and not response.cancelled:
            self.memory.add_message(
                self._active_conversation_id,
                "assistant",
                response.text,
                language=self.config.ai.language_mode.value,
            )

        self._set_state(AssistantState.IDLE)
        return TextSubmitResult(
            accepted=True,
            user_text=cleaned,
            backend_connected=True,
            system_notice="Generation cancelled." if response.cancelled else "",
            conversation_id=self._active_conversation_id,
            assistant_text=response.text,
            tokens_generated=response.tokens_generated,
            tokens_per_sec=response.tokens_per_sec,
            cancelled=response.cancelled,
        )

    def update_settings(
        self,
        *,
        double_clap_enabled: bool | None = None,
        language_mode: LanguageMode | None = None,
        memory_profile: MemoryProfile | None = None,
        selected_model_slug: str | None = None,
        persist: bool = True,
    ) -> PrimeConfig:
        """Update supported settings safely and optionally persist to config.toml."""
        new_activation = self.config.activation
        if double_clap_enabled is not None:
            new_activation = ActivationConfig(
                push_to_talk_enabled=self.config.activation.push_to_talk_enabled,
                double_clap_enabled=bool(double_clap_enabled),
                wake_word_enabled=False,
                background_mic_enabled=False,
                clap_threshold=self.config.activation.clap_threshold,
                clap_min_interval_s=self.config.activation.clap_min_interval_s,
                clap_max_interval_s=self.config.activation.clap_max_interval_s,
            )

        new_ai = self.config.ai
        if (
            language_mode is not None
            or memory_profile is not None
            or selected_model_slug is not None
        ):
            new_profile = memory_profile or self.config.ai.memory_profile
            ctx_by_profile = {
                MemoryProfile.ECO: 2048,
                MemoryProfile.BALANCED: 4096,
                MemoryProfile.HEAVY: 2048,
            }
            new_budget = default_budget_for_profile(new_profile)
            new_slug = selected_model_slug or self.config.ai.selected_model_slug
            self._model_registry.get_spec(new_slug)
            new_ai = HardwareAIConfig(
                memory_profile=new_profile,
                language_mode=language_mode or self.config.ai.language_mode,
                local_only=True,
                max_context_tokens=ctx_by_profile[new_profile],
                idle_unload_seconds=self.config.ai.idle_unload_seconds,
                selected_model_slug=new_slug,
                memory_budget_mb=new_budget,
                max_generation_tokens=self.config.ai.max_generation_tokens,
                auto_load_model=self.config.ai.auto_load_model,
            )
            self.runtime.select_model(new_slug)
            self.runtime.update_memory_budget(
                new_budget, new_ai.max_context_tokens, new_ai.max_generation_tokens
            )

        self.config = replace(self.config, activation=new_activation, ai=new_ai)
        self.context = ContextAssembler(self.memory, language_mode=self.config.ai.language_mode)
        if persist:
            save_config_toml(self.config)
        self.events.publish("config.updated", self.config.to_safe_dict())
        return self.config

    @classmethod
    def from_environment(
        cls,
        *,
        config_path: Path | None = None,
        confirmation_handler: ConfirmationHandler | None = None,
        console_logging: bool = False,
    ) -> PrimeApp:
        cfg = load_config(config_path=config_path)
        return cls(
            cfg,
            confirmation_handler=confirmation_handler,
            console_logging=console_logging,
        )

    def bootstrap(self) -> PrimeStatusSnapshot:
        """Initialize local storage, verify adapters, and transition to IDLE."""
        if self.state != AssistantState.STOPPED:
            return self.status()

        self._set_state(AssistantState.STARTING)
        self._schema_version = self.memory.initialize()
        self._set_state(AssistantState.IDLE)

        log_event(
            self.logger,
            logging.INFO,
            "prime.bootstrap",
            "PRIME core foundation initialized",
            context={
                "bundle_id": self.config.identity.bundle_id,
                "platform": self.system.platform_kind.value,
                "schema_version": self._schema_version,
                "fts5_enabled": self.memory.fts5_enabled,
                "memory_profile": self.config.ai.memory_profile.value,
                "language_mode": self.config.ai.language_mode.value,
            },
        )
        return self.status()

    def status(self) -> PrimeStatusSnapshot:
        return PrimeStatusSnapshot(
            app_name=self.config.identity.app_name,
            bundle_id=self.config.identity.bundle_id,
            version=self.config.identity.version,
            state=self.state,
            platform=self.system.platform_kind,
            schema_version=self._schema_version,
            fts5_enabled=self.memory.fts5_enabled,
            memory_profile=self.config.ai.memory_profile.value,
            language_mode=self.config.ai.language_mode.value,
            local_only=self.config.ai.local_only,
        )

    def shutdown(self) -> None:
        if self.state == AssistantState.STOPPED:
            return
        self._set_state(AssistantState.SHUTTING_DOWN)
        self.runtime.unload_model()
        self.plugins.unregister_all()
        self.memory.close()
        log_event(
            self.logger,
            logging.INFO,
            "prime.shutdown",
            "PRIME core shutdown complete",
        )
        self._set_state(AssistantState.STOPPED)

    def _set_state(self, new_state: AssistantState) -> None:
        old_state = self.state
        self.state = new_state
        self.events.publish(
            "assistant.state_changed",
            {"from": old_state.value, "to": new_state.value},
        )
