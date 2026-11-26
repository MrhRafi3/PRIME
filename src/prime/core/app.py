"""PRIME core application bootstrap, wiring, and graceful lifecycle management."""

from __future__ import annotations

import logging
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
from prime.intelligence.memory.store import MemoryStore
from prime.intelligence.providers.base import LLMProvider
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


class PrimeApp:
    """Coordinates PRIME core modules with clean bootstrap and shutdown."""

    def __init__(
        self,
        config: PrimeConfig,
        *,
        confirmation_handler: ConfirmationHandler | None = None,
        llm_provider: LLMProvider | None = None,
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
        self._llm_provider = llm_provider
        self._active_conversation_id: int | None = None
        self._push_to_talk_pressed = False
        self._schema_version = 0

    @property
    def ai_backend_connected(self) -> bool:
        return self._llm_provider is not None and self._llm_provider.is_loaded

    @property
    def active_conversation_id(self) -> int | None:
        return self._active_conversation_id

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

    def submit_text_message(self, text: str) -> TextSubmitResult:
        """Process a user text input honestly; never fabricate AI output when offline."""
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
            notice = (
                "Local AI engine is not connected in Phase 03. "
                "Your message was saved locally; inference will be enabled in a later phase."
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

        self._set_state(AssistantState.IDLE)
        return TextSubmitResult(
            accepted=True,
            user_text=cleaned,
            backend_connected=True,
            system_notice="",
            conversation_id=self._active_conversation_id,
        )

    def update_settings(
        self,
        *,
        double_clap_enabled: bool | None = None,
        language_mode: LanguageMode | None = None,
        memory_profile: MemoryProfile | None = None,
        persist: bool = True,
    ) -> PrimeConfig:
        """Update supported Phase 03 settings safely and optionally persist to config.toml."""
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
        if language_mode is not None or memory_profile is not None:
            new_profile = memory_profile or self.config.ai.memory_profile
            ctx_by_profile = {
                MemoryProfile.ECO: 2048,
                MemoryProfile.BALANCED: 4096,
                MemoryProfile.HEAVY: 2048,
            }
            new_ai = HardwareAIConfig(
                memory_profile=new_profile,
                language_mode=language_mode or self.config.ai.language_mode,
                local_only=True,
                max_context_tokens=ctx_by_profile[new_profile],
                idle_unload_seconds=self.config.ai.idle_unload_seconds,
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
