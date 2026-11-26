"""Runtime state machine managing local model lifecycle, streaming, and unload."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from prime.config.settings import MemoryProfile
from prime.intelligence.generation.service import GenerationConfig, GenerationService
from prime.intelligence.models.registry import ApprovedModelSpec, ModelRegistry
from prime.intelligence.providers.base import (
    ChatMessage,
    GenerationResponse,
    LLMProvider,
    ModelSpec,
    StreamChunk,
)
from prime.logging.logger import get_logger, log_event
from prime.system.base import StrEnum


class RuntimeState(StrEnum):
    MODEL_NOT_INSTALLED = "Model Not Installed"
    MODEL_AVAILABLE = "Model Available"
    LOADING_MODEL = "Loading Model"
    READY = "Ready"
    THINKING = "Thinking"
    STREAMING_RESPONSE = "Streaming Response"
    CANCELLING = "Cancelling"
    ERROR = "Error"


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    state: RuntimeState
    selected_model_slug: str
    active_model_name: str
    installed_models: tuple[str, ...]
    tokens_per_sec: float = 0.0
    last_token_count: int = 0
    memory_mb: float = 0.0
    error_message: str = ""


class LocalAIRuntime:
    """Coordinates ModelRegistry, LLMProvider, and GenerationService safely."""

    def __init__(
        self,
        registry: ModelRegistry,
        provider: LLMProvider,
        *,
        generation_config: GenerationConfig | None = None,
        selected_model_slug: str = "qwen2.5-1.5b-4bit",
        logger: logging.Logger | None = None,
    ) -> None:
        self._registry = registry
        self._provider = provider
        self._generation = GenerationService(provider, generation_config or GenerationConfig())
        self._selected_slug = selected_model_slug
        self._logger = logger or get_logger("prime.intelligence.runtime")
        self._state = self._compute_idle_state()
        self._last_tps = 0.0
        self._last_tokens = 0
        self._error_message = ""
        self._listeners: list[Callable[[RuntimeSnapshot], None]] = []

    def subscribe(self, listener: Callable[[RuntimeSnapshot], None]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[[RuntimeSnapshot], None]) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    @property
    def is_ready(self) -> bool:
        return self._provider.is_loaded and self._state in {
            RuntimeState.READY,
            RuntimeState.THINKING,
            RuntimeState.STREAMING_RESPONSE,
            RuntimeState.CANCELLING,
        }

    def snapshot(self) -> RuntimeSnapshot:
        installed = tuple(m.slug for m in self._registry.list_installed())
        active_name = "None"
        if self._provider.is_loaded and self._provider.active_model_id:
            try:
                active_name = self._registry.get_spec(self._provider.active_model_id).display_name
            except Exception:
                active_name = self._provider.active_model_id
        elif self._selected_slug:
            try:
                active_name = self._registry.get_spec(self._selected_slug).display_name
            except Exception:
                active_name = self._selected_slug

        mem = self._provider.memory_report().active_memory_mb if self._provider.is_loaded else 0.0
        return RuntimeSnapshot(
            state=self._state,
            selected_model_slug=self._selected_slug,
            active_model_name=active_name,
            installed_models=installed,
            tokens_per_sec=self._last_tps,
            last_token_count=self._last_tokens,
            memory_mb=mem,
            error_message=self._error_message,
        )

    def refresh_availability(self) -> RuntimeSnapshot:
        if not self._provider.is_loaded:
            self._error_message = ""
            self._set_state(self._compute_idle_state())
        return self.snapshot()

    def select_model(self, slug: str) -> RuntimeSnapshot:
        self._registry.get_spec(slug)
        self._selected_slug = slug
        if not self._provider.is_loaded:
            self._error_message = ""
            self._set_state(self._compute_idle_state())
        return self.snapshot()

    def update_memory_budget(self, budget_mb: int, max_ctx: int, max_gen: int) -> None:
        self._generation.update_config(
            GenerationConfig(
                memory_budget_mb=budget_mb,
                max_context_tokens=max_ctx,
                max_generation_tokens=max_gen,
                temperature=self._generation.config.temperature,
                top_p=self._generation.config.top_p,
            )
        )

    def load_model(self, slug: str | None = None) -> RuntimeSnapshot:
        target_slug = slug or self._selected_slug
        spec_info: ApprovedModelSpec = self._registry.get_spec(target_slug)
        self._selected_slug = target_slug

        if not self._registry.is_installed(target_slug):
            self._error_message = f"Model '{spec_info.display_name}' is not installed locally."
            self._set_state(RuntimeState.MODEL_NOT_INSTALLED)
            raise FileNotFoundError(self._error_message)

        model_path = self._registry.resolve_model_path(target_slug)
        provider_spec = ModelSpec(
            model_id=spec_info.slug,
            backend="mlx",
            quantization="4bit",
            estimated_ram_mb=spec_info.estimated_ram_mb,
            max_context_tokens=min(
                spec_info.max_context_tokens, self._generation.config.max_context_tokens
            ),
            supports_bangla=spec_info.supports_bangla,
        )

        self._generation.check_memory_budget(provider_spec)
        self._error_message = ""
        self._set_state(RuntimeState.LOADING_MODEL)
        try:
            self._provider.initialize()
            self._provider.load(provider_spec, model_path=model_path)
            self._set_state(RuntimeState.READY)
            log_event(
                self._logger,
                logging.INFO,
                "ai.model_loaded",
                "Local model loaded into memory",
                context={
                    "model_id": target_slug,
                    "estimated_ram_mb": spec_info.estimated_ram_mb,
                },
            )
            return self.snapshot()
        except Exception as exc:
            self._error_message = str(exc)
            self._set_state(RuntimeState.ERROR)
            log_event(
                self._logger,
                logging.ERROR,
                "ai.model_load_failed",
                f"Failed to load local model: {exc}",
                context={"model_id": target_slug},
            )
            raise

    def unload_model(self) -> RuntimeSnapshot:
        self._provider.unload()
        self._last_tps = 0.0
        self._last_tokens = 0
        self._error_message = ""
        self._set_state(self._compute_idle_state())
        log_event(
            self._logger,
            logging.INFO,
            "ai.model_unloaded",
            "Local model unloaded from memory",
        )
        return self.snapshot()

    def cancel_generation(self) -> RuntimeSnapshot:
        if self._state in {RuntimeState.THINKING, RuntimeState.STREAMING_RESPONSE}:
            self._set_state(RuntimeState.CANCELLING)
        self._generation.cancel()
        return self.snapshot()

    def generate_stream(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        on_token: Callable[[str, StreamChunk], None] | None = None,
    ) -> GenerationResponse:
        if not self._provider.is_loaded:
            self._set_state(self._compute_idle_state())
            raise RuntimeError("No local model is currently loaded.")

        self._error_message = ""
        self._set_state(RuntimeState.THINKING)

        def _handle_chunk(chunk: StreamChunk) -> None:
            if chunk.text and self._state == RuntimeState.THINKING:
                self._set_state(RuntimeState.STREAMING_RESPONSE)
            self._last_tokens = chunk.token_count
            if chunk.tokens_per_sec > 0:
                self._last_tps = chunk.tokens_per_sec
            if on_token is not None and chunk.text:
                on_token(chunk.text, chunk)

        try:
            response = self._generation.stream(messages, on_chunk=_handle_chunk)
            self._last_tokens = response.tokens_generated
            if response.tokens_per_sec > 0:
                self._last_tps = response.tokens_per_sec
            self._set_state(RuntimeState.READY)
            return response
        except Exception as exc:
            self._error_message = str(exc)
            self._set_state(RuntimeState.ERROR)
            log_event(
                self._logger,
                logging.ERROR,
                "ai.generation_error",
                f"Local generation failed: {exc}",
            )
            raise

    def _compute_idle_state(self) -> RuntimeState:
        if self._registry.is_installed(self._selected_slug) or self._registry.list_installed():
            return RuntimeState.MODEL_AVAILABLE
        return RuntimeState.MODEL_NOT_INSTALLED

    def _set_state(self, new_state: RuntimeState) -> None:
        self._state = new_state
        snap = self.snapshot()
        for listener in list(self._listeners):
            listener(snap)


def default_budget_for_profile(profile: MemoryProfile) -> int:
    if profile == MemoryProfile.ECO:
        return 2200
    if profile == MemoryProfile.BALANCED:
        return 3200
    return 5200
