"""Apple Silicon MLX-LM local inference provider (100% offline)."""

from __future__ import annotations

import gc
import logging
import os
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from prime.intelligence.providers.base import (
    GenerationRequest,
    GenerationResponse,
    ModelSpec,
    ProviderMemoryReport,
    ProviderNotConfiguredError,
    ProviderStatus,
    StreamChunk,
)


class MLXProvider:
    """Offline MLX-LM provider with lazy import, streaming, cancellation, and unload."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._status = ProviderStatus.UNINITIALIZED
        self._model: Any = None
        self._tokenizer: Any = None
        self._spec: ModelSpec | None = None
        self._model_path: Path | None = None
        self._cancel_event = threading.Event()
        self._last_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    @property
    def active_model_id(self) -> str | None:
        return self._spec.model_id if self._spec is not None else None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def initialize(self) -> None:
        """Confirm MLX and Metal availability without loading weights."""
        with self._lock:
            try:
                import mlx.core as mx
                import mlx_lm  # noqa: F401
            except Exception as exc:
                self._status = ProviderStatus.ERROR
                self._last_error = f"MLX backend unavailable: {exc}"
                raise RuntimeError(self._last_error) from exc

            if not mx.metal.is_available():
                self._status = ProviderStatus.ERROR
                self._last_error = "Apple Silicon Metal GPU is not available."
                raise RuntimeError(self._last_error)

            self._last_error = None
            if not self.is_loaded:
                self._status = ProviderStatus.READY

    def is_model_available(self, model_path: Path) -> bool:
        return (
            model_path.is_dir()
            and (model_path / "config.json").is_file()
            and any(model_path.glob("*.safetensors"))
        )

    def load(self, spec: ModelSpec, *, model_path: Path | None = None) -> None:
        if model_path is None or not self.is_model_available(model_path):
            raise FileNotFoundError(
                f"Local model files not found at {model_path!s}. Download must be approved first."
            )

        with self._lock:
            self.unload()
            self._status = ProviderStatus.LOADING
            self._last_error = None
            # Enforce strict offline mode for Hugging Face / transformers during local load.
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            try:
                import mlx_lm

                model, tokenizer = mlx_lm.load(str(model_path))
                self._model = model
                self._tokenizer = tokenizer
                self._spec = spec
                self._model_path = model_path
                self._status = ProviderStatus.LOADED
            except MemoryError as exc:
                self._status = ProviderStatus.ERROR
                self._last_error = f"Out of memory loading {spec.model_id}: {exc}"
                self.unload()
                raise
            except Exception as exc:
                self._status = ProviderStatus.ERROR
                self._last_error = f"Failed to load {spec.model_id}: {exc}"
                self.unload()
                raise RuntimeError(self._last_error) from exc

    def unload(self) -> None:
        with self._lock:
            self._cancel_event.set()
            self._model = None
            self._tokenizer = None
            self._spec = None
            self._model_path = None
            gc.collect()
            try:
                import mlx.core as mx

                if hasattr(mx, "clear_cache"):
                    mx.clear_cache()
            except Exception as exc:
                logging.getLogger("prime.intelligence.mlx").debug(
                    "MLX cache clear skipped during unload: %s", exc
                )
            if self._status != ProviderStatus.ERROR:
                self._status = ProviderStatus.READY

    def cancel(self) -> None:
        self._cancel_event.set()

    def status(self) -> ProviderStatus:
        return self._status

    def memory_report(self) -> ProviderMemoryReport:
        try:
            import mlx.core as mx

            get_active = getattr(mx, "get_active_memory", None) or mx.metal.get_active_memory
            get_peak = getattr(mx, "get_peak_memory", None) or mx.metal.get_peak_memory
            active_mb = round(get_active() / (1024 * 1024), 2)
            peak_mb = round(get_peak() / (1024 * 1024), 2)
            return ProviderMemoryReport(
                backend="mlx",
                active_memory_mb=active_mb,
                peak_memory_mb=peak_mb,
            )
        except Exception:
            return ProviderMemoryReport(backend="mlx", active_memory_mb=0.0, peak_memory_mb=0.0)

    def _format_prompt(self, request: GenerationRequest) -> str:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        tokenizer = self._tokenizer
        if hasattr(tokenizer, "apply_chat_template"):
            try:
                return str(
                    tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True,
                        enable_thinking=False,
                    )
                )
            except TypeError:
                try:
                    return str(
                        tokenizer.apply_chat_template(
                            messages,
                            tokenize=False,
                            add_generation_prompt=True,
                        )
                    )
                except Exception as exc:
                    logging.getLogger("prime.intelligence.mlx").debug(
                        "Tokenizer chat template unavailable, using fallback format: %s", exc
                    )
            except Exception as exc:
                logging.getLogger("prime.intelligence.mlx").debug(
                    "Tokenizer chat template unavailable, using fallback format: %s", exc
                )
        # Fallback plain role formatting if a tokenizer lacks a chat template
        parts = [f"<|{m['role']}|>\n{m['content']}" for m in messages]
        parts.append("<|assistant|>\n")
        return "\n".join(parts)

    def stream_generate(
        self,
        request: GenerationRequest,
        *,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[StreamChunk]:
        if not self.is_loaded:
            raise ProviderNotConfiguredError("No local MLX model is currently loaded.")

        self._cancel_event.clear()
        self._status = ProviderStatus.GENERATING
        prompt = self._format_prompt(request)
        start = time.perf_counter()

        try:
            import mlx_lm
            from mlx_lm.sample_utils import make_sampler

            sampler = make_sampler(temp=request.temperature, top_p=request.top_p)
            token_count = 0
            for resp in mlx_lm.stream_generate(
                self._model,
                self._tokenizer,
                prompt=prompt,
                max_tokens=request.max_tokens,
                sampler=sampler,
            ):
                if self._cancel_event.is_set() or (cancel_event and cancel_event.is_set()):
                    elapsed = max(0.001, time.perf_counter() - start)
                    yield StreamChunk(
                        text="",
                        token_count=token_count,
                        tokens_per_sec=round(token_count / elapsed, 2),
                        finish_reason="cancelled",
                        peak_memory_gb=float(getattr(resp, "peak_memory", 0.0)),
                    )
                    return

                token_count = int(getattr(resp, "generation_tokens", token_count + 1))
                tps = float(getattr(resp, "generation_tps", 0.0))
                yield StreamChunk(
                    text=str(getattr(resp, "text", "")),
                    token_count=token_count,
                    tokens_per_sec=round(tps, 2),
                    finish_reason=getattr(resp, "finish_reason", None),
                    peak_memory_gb=float(getattr(resp, "peak_memory", 0.0)),
                )
        except MemoryError as exc:
            self._status = ProviderStatus.ERROR
            self._last_error = f"MLX out-of-memory error: {exc}"
            raise
        except Exception as exc:
            self._status = ProviderStatus.ERROR
            self._last_error = f"MLX generation error: {exc}"
            raise RuntimeError(self._last_error) from exc
        finally:
            if self.is_loaded and self._status != ProviderStatus.ERROR:
                self._status = ProviderStatus.LOADED

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        chunks: list[str] = []
        tokens = 0
        tps = 0.0
        finish: str | None = None
        cancelled = False
        for chunk in self.stream_generate(request):
            if chunk.text:
                chunks.append(chunk.text)
            tokens = chunk.token_count
            tps = chunk.tokens_per_sec
            finish = chunk.finish_reason
            if finish == "cancelled":
                cancelled = True
                break
        return GenerationResponse(
            text="".join(chunks).strip(),
            model_id=self.active_model_id or "",
            tokens_generated=tokens,
            tokens_per_sec=tps,
            cancelled=cancelled,
            finish_reason=finish,
        )
