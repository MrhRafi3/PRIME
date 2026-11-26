"""Unit and integration tests for PRIME Phase 04 Local Intelligence Engine."""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle

from prime.config import LanguageMode, MemoryProfile, load_config
from prime.core import PrimeApp
from prime.intelligence.generation import GenerationConfig, MemoryBudgetError
from prime.intelligence.models import ApprovedModelSpec, ModelRegistry, ModelSecurityError
from prime.intelligence.prompts import load_system_prompt
from prime.intelligence.providers import (
    ChatMessage,
    GenerationRequest,
    GenerationResponse,
    MLXProvider,
    ModelSpec,
    ProviderMemoryReport,
    ProviderNotConfiguredError,
    ProviderStatus,
    StreamChunk,
)
from prime.intelligence.runtime import LocalAIRuntime, RuntimeState
from prime.ui.bridge import PrimeUIBridge


class _MockLLMProvider:
    """Deterministic offline mock implementing LLMProvider for tests."""

    def __init__(
        self,
        *,
        tokens: tuple[str, ...] = ("Hello ", "from ", "PRIME!"),
        fail_on_load: Exception | None = None,
        fail_on_generate: Exception | None = None,
        delay_cancel_check: bool = False,
    ) -> None:
        self._loaded = False
        self._model_id: str | None = None
        self._status = ProviderStatus.UNINITIALIZED
        self._cancel_event = threading.Event()
        self._tokens = tokens
        self._fail_on_load = fail_on_load
        self._fail_on_generate = fail_on_generate
        self._delay_cancel_check = delay_cancel_check
        self.last_request: GenerationRequest | None = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def active_model_id(self) -> str | None:
        return self._model_id

    def initialize(self) -> None:
        if self._status == ProviderStatus.UNINITIALIZED:
            self._status = ProviderStatus.READY

    def is_model_available(self, model_path: Path) -> bool:
        return (model_path / "config.json").is_file() and any(model_path.glob("*.safetensors"))

    def load(self, spec: ModelSpec, *, model_path: Path | None = None) -> None:
        self._status = ProviderStatus.LOADING
        if self._fail_on_load is not None:
            self._status = ProviderStatus.ERROR
            raise self._fail_on_load
        if model_path is None or not self.is_model_available(model_path):
            raise FileNotFoundError("Missing local model files")
        self._loaded = True
        self._model_id = spec.model_id
        self._status = ProviderStatus.LOADED

    def unload(self) -> None:
        self._cancel_event.set()
        self._loaded = False
        self._model_id = None
        self._status = ProviderStatus.READY

    def cancel(self) -> None:
        self._cancel_event.set()

    def status(self) -> ProviderStatus:
        return self._status

    def memory_report(self) -> ProviderMemoryReport:
        return ProviderMemoryReport(
            backend="mock-mlx",
            active_memory_mb=1400.0 if self._loaded else 0.0,
            peak_memory_mb=1450.0 if self._loaded else 0.0,
        )

    def stream_generate(
        self,
        request: GenerationRequest,
        *,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[StreamChunk]:
        if not self._loaded:
            raise ProviderNotConfiguredError("Model not loaded")
        self._cancel_event.clear()
        self._status = ProviderStatus.GENERATING
        self.last_request = request
        try:
            if self._fail_on_generate is not None:
                self._status = ProviderStatus.ERROR
                raise self._fail_on_generate
            for idx, tok in enumerate(self._tokens):
                if self._delay_cancel_check and idx == 1:
                    self._cancel_event.set()
                if self._cancel_event.is_set() or (cancel_event and cancel_event.is_set()):
                    yield StreamChunk(
                        text="",
                        token_count=idx,
                        tokens_per_sec=32.0,
                        finish_reason="cancelled",
                    )
                    return
                token_num = idx + 1
                yield StreamChunk(
                    text=tok,
                    token_count=token_num,
                    tokens_per_sec=35.0,
                    finish_reason="stop" if idx == len(self._tokens) - 1 else None,
                )
        finally:
            if self._loaded and self._status != ProviderStatus.ERROR:
                self._status = ProviderStatus.LOADED

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        parts: list[str] = []
        count = 0
        for chunk in self.stream_generate(request):
            if chunk.text:
                parts.append(chunk.text)
            count = chunk.token_count
        return GenerationResponse(
            text="".join(parts).strip(),
            model_id=self._model_id or "",
            tokens_generated=count,
            tokens_per_sec=35.0,
        )


def _create_fake_local_model(models_dir: Path, slug: str) -> Path:
    model_dir = models_dir / slug
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_text('{"model_type": "qwen2"}', encoding="utf-8")
    (model_dir / "model.safetensors").write_bytes(b"fake-weights")
    return model_dir


@pytest.mark.unit
def test_external_system_prompt_loader() -> None:
    prompt = load_system_prompt(
        language_mode=LanguageMode.BANGLA_ENGLISH,
        notes=("Hardware: MacBook Air M1 8GB",),
    )
    assert "PRIME" in prompt
    assert "Bangla" in prompt
    assert "Banglish" in prompt
    assert "MacBook Air M1 8GB" in prompt


@pytest.mark.unit
def test_model_registry_approval_and_path_safety(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    reg = ModelRegistry(models_dir)

    assert reg.list_installed() == ()
    assert reg.is_installed("qwen2.5-1.5b-4bit") is False

    with pytest.raises(ModelSecurityError):
        reg.get_spec("../evil-model")
    with pytest.raises(ModelSecurityError):
        reg.resolve_model_path("unapproved-random-repo")

    _create_fake_local_model(models_dir, "qwen2.5-1.5b-4bit")
    assert reg.is_installed("qwen2.5-1.5b-4bit") is True
    assert len(reg.list_installed()) == 1
    assert reg.installed_size_mb("qwen2.5-1.5b-4bit") >= 0.0


@pytest.mark.unit
def test_mlx_provider_offline_contract_without_weights(tmp_path: Path) -> None:
    provider = MLXProvider()
    assert provider.is_loaded is False
    assert provider.status() == ProviderStatus.UNINITIALIZED
    provider.initialize()
    assert provider.status() == ProviderStatus.READY
    assert provider.is_model_available(tmp_path / "missing") is False

    spec = ModelSpec("qwen2.5-1.5b-4bit", "mlx", "4bit", 1400, 4096)
    with pytest.raises(FileNotFoundError):
        provider.load(spec, model_path=tmp_path / "missing")
    with pytest.raises(ProviderNotConfiguredError):
        list(provider.stream_generate(GenerationRequest(messages=(ChatMessage("user", "hi"),))))


@pytest.mark.unit
def test_runtime_lifecycle_streaming_cancellation_and_budget(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    _create_fake_local_model(models_dir, "qwen2.5-1.5b-4bit")
    _create_fake_local_model(models_dir, "qwen2.5-3b-4bit")

    registry = ModelRegistry(models_dir)
    provider = _MockLLMProvider(tokens=("স্বাগতম ", "PRIME ", "থেকে!"))
    runtime = LocalAIRuntime(
        registry,
        provider,
        generation_config=GenerationConfig(memory_budget_mb=2000),
        selected_model_slug="qwen2.5-1.5b-4bit",
    )

    observed_states: list[RuntimeState] = []
    runtime.subscribe(lambda snap: observed_states.append(snap.state))

    # Not auto-loaded at startup
    assert runtime.snapshot().state == RuntimeState.MODEL_AVAILABLE
    assert runtime.is_ready is False

    # Memory budget blocks 3B model when budget is 2000 MB
    with pytest.raises(MemoryBudgetError):
        runtime.load_model("qwen2.5-3b-4bit")

    # 1.5B fits budget and loads cleanly
    snap = runtime.load_model("qwen2.5-1.5b-4bit")
    assert snap.state == RuntimeState.READY
    assert snap.memory_mb == 1400.0

    # Streaming Bangla tokens
    chunks: list[str] = []
    resp = runtime.generate_stream(
        (ChatMessage("user", "বাংলায় বলো"),),
        on_token=lambda delta, _c: chunks.append(delta),
    )
    assert "".join(chunks) == "স্বাগতম PRIME থেকে!"
    assert resp.tokens_generated == 3
    assert resp.cancelled is False
    assert RuntimeState.THINKING in observed_states
    assert RuntimeState.STREAMING_RESPONSE in observed_states
    assert runtime.snapshot().state == RuntimeState.READY

    # Unload releases memory
    unloaded = runtime.unload_model()
    assert unloaded.state == RuntimeState.MODEL_AVAILABLE
    assert unloaded.memory_mb == 0.0

    # Cancellation during streaming
    cancel_provider = _MockLLMProvider(
        tokens=("First ", "Second ", "Third"),
        delay_cancel_check=True,
    )
    cancel_runtime = LocalAIRuntime(
        registry,
        cancel_provider,
        generation_config=GenerationConfig(memory_budget_mb=2000),
        selected_model_slug="qwen2.5-1.5b-4bit",
    )
    cancel_runtime.load_model("qwen2.5-1.5b-4bit")
    c_resp = cancel_runtime.generate_stream((ChatMessage("user", "test cancel"),))
    assert c_resp.cancelled is True
    assert c_resp.text == "First"

    # Simulated OOM / generation error transitions cleanly to ERROR
    oom_provider = _MockLLMProvider(fail_on_generate=MemoryError("Metal OOM"))
    err_runtime = LocalAIRuntime(
        registry,
        oom_provider,
        generation_config=GenerationConfig(memory_budget_mb=2000),
        selected_model_slug="qwen2.5-1.5b-4bit",
    )
    err_runtime.load_model("qwen2.5-1.5b-4bit")
    with pytest.raises(MemoryError):
        err_runtime.generate_stream((ChatMessage("user", "oom"),))
    assert err_runtime.snapshot().state == RuntimeState.ERROR


@pytest.mark.integration
def test_prime_app_bangla_english_conversation_and_ui_bridge(tmp_path: Path) -> None:
    if QGuiApplication.instance() is None:
        QGuiApplication(["prime-test"])
        QQuickStyle.setStyle("Basic")

    models_dir = tmp_path / "models"
    _create_fake_local_model(models_dir, "qwen2.5-1.5b-4bit")

    cfg = load_config(
        env={
            "PRIME_DATA_DIR": str(tmp_path / "data"),
            "PRIME_LOG_DIR": str(tmp_path / "logs"),
            "PRIME_MODELS_DIR": str(models_dir),
            "PRIME_MEMORY_PROFILE": "eco",
            "PRIME_MODEL_SLUG": "qwen2.5-1.5b-4bit",
            "PRIME_ENVIRONMENT": "test",
        }
    )
    custom_catalog = {
        "qwen2.5-1.5b-4bit": ApprovedModelSpec(
            slug="qwen2.5-1.5b-4bit",
            display_name="Qwen 2.5 1.5B Instruct (4-bit MLX)",
            repo_id="mlx-community/Qwen2.5-1.5B-Instruct-4bit",
            download_size_gb=0.90,
            estimated_ram_mb=1400,
            memory_profile=MemoryProfile.ECO,
            license_name="Apache-2.0",
            max_context_tokens=4096,
        )
    }
    provider = _MockLLMProvider(tokens=("হ্যাঁ রাফি, ", "আমি প্রস্তুত।"))
    app = PrimeApp(
        cfg,
        llm_provider=provider,
        model_registry=ModelRegistry(models_dir, catalog=custom_catalog),
        platform_override="darwin",
    )
    app.bootstrap()
    bridge = PrimeUIBridge(app, start_timers=False)

    try:
        # Before loading: no fabricated response
        assert bridge.aiBackendConnected is False
        assert bridge.runtimeStateText == RuntimeState.MODEL_AVAILABLE.value
        bridge.sendMessage("Tumi kemon acho?")
        assert bridge.messagesModel.rowCount() == 2

        # Load model via UI bridge and send Bangla prompt
        bridge.loadModel()
        assert bridge.aiBackendConnected is True
        assert bridge.runtimeStateText == RuntimeState.READY.value

        bridge.sendMessage("বাংলায় উত্তর দাও")
        assert bridge.messagesModel.rowCount() == 4
        last_idx = bridge.messagesModel.index(3, 0)
        assert bridge.messagesModel.data(last_idx, bridge.messagesModel.RoleRole) == "PRIME"
        assert "আমি প্রস্তুত।" in bridge.messagesModel.data(last_idx, bridge.messagesModel.TextRole)

        # Verify SQLite persisted both user and assistant messages locally
        assert app.active_conversation_id is not None
        history = app.memory.get_messages(app.active_conversation_id)
        roles_and_text = [(m.role, m.content) for m in history]
        assert ("user", "বাংলায় উত্তর দাও") in roles_and_text
        assert ("assistant", "হ্যাঁ রাফি, আমি প্রস্তুত।") in roles_and_text

        # Unload cleanly
        bridge.unloadModel()
        assert bridge.aiBackendConnected is False
        assert bridge.runtimeStateText == RuntimeState.MODEL_AVAILABLE.value
    finally:
        bridge.shutdown()
        app.shutdown()


@pytest.mark.unit
def test_no_model_installed_state(tmp_path: Path) -> None:
    cfg = load_config(
        env={
            "PRIME_DATA_DIR": str(tmp_path / "data"),
            "PRIME_LOG_DIR": str(tmp_path / "logs"),
            "PRIME_MODELS_DIR": str(tmp_path / "empty_models"),
            "PRIME_ENVIRONMENT": "test",
        }
    )
    app = PrimeApp(cfg, llm_provider=_MockLLMProvider(), platform_override="darwin")
    app.bootstrap()
    try:
        assert app.get_runtime_snapshot().state == RuntimeState.MODEL_NOT_INSTALLED
        res = app.submit_text_message("Hello?")
        assert res.backend_connected is False
        assert "No local AI model is installed" in res.system_notice
        assert res.assistant_text == ""
    finally:
        app.shutdown()
