"""Offline local model benchmark script for PRIME (Apple Silicon M1 8GB).

Benchmarks ONLY models already installed locally under PRIME's models directory.
Never initiates automatic network downloads.
"""

from __future__ import annotations

import json
import resource
import sys
import time

from prime.config import load_config
from prime.intelligence.models import ModelRegistry
from prime.intelligence.prompts import load_system_prompt
from prime.intelligence.providers import ChatMessage, GenerationRequest, MLXProvider, ModelSpec

PROMPTS = [
    ("english", "In two concise sentences, explain what unified memory means on Apple Silicon."),
    ("bangla", "সংক্ষেপে দুই বাক্যে বলো কৃত্রিম বুদ্ধিমত্তা কীভাবে দৈনন্দিন কাজে সাহায্য করে।"),
    ("banglish", "Amar laptop M1 8GB RAM, eta ki local AI er jonno valo?"),
]


def _max_rss_mb() -> float:
    # ru_maxrss is in bytes on macOS
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024), 2)


def main() -> int:
    cfg = load_config()
    registry = ModelRegistry(cfg.storage.models_dir)
    installed = registry.list_installed()
    if not installed:
        print(
            f"No approved local models installed in {registry.models_dir}. "
            "Approve and install a model before running benchmarks.",
            file=sys.stderr,
        )
        return 1

    provider = MLXProvider()
    provider.initialize()
    system_prompt = load_system_prompt(language_mode=cfg.ai.language_mode)
    results = []

    for spec_info in installed:
        model_path = registry.resolve_model_path(spec_info.slug)
        spec = ModelSpec(
            model_id=spec_info.slug,
            backend="mlx",
            quantization="4bit",
            estimated_ram_mb=spec_info.estimated_ram_mb,
            max_context_tokens=min(spec_info.max_context_tokens, 4096),
        )
        t0 = time.perf_counter()
        provider.load(spec, model_path=model_path)
        load_s = round(time.perf_counter() - t0, 2)

        prompt_runs = []
        for label, prompt_text in PROMPTS:
            req = GenerationRequest(
                messages=(
                    ChatMessage("system", system_prompt),
                    ChatMessage("user", prompt_text),
                ),
                max_tokens=160,
                temperature=0.3,
            )
            g0 = time.perf_counter()
            resp = provider.generate(req)
            elapsed_s = round(time.perf_counter() - g0, 2)
            mem = provider.memory_report()
            prompt_runs.append(
                {
                    "kind": label,
                    "tokens": resp.tokens_generated,
                    "tokens_per_sec": resp.tokens_per_sec,
                    "elapsed_s": elapsed_s,
                    "mlx_active_mb": mem.active_memory_mb,
                    "mlx_peak_mb": mem.peak_memory_mb,
                    "preview": resp.text[:240],
                }
            )

        provider.unload()
        post_unload_mem = provider.memory_report()
        results.append(
            {
                "slug": spec_info.slug,
                "disk_mb": registry.installed_size_mb(spec_info.slug),
                "load_time_s": load_s,
                "process_max_rss_mb": _max_rss_mb(),
                "post_unload_active_mb": post_unload_mem.active_memory_mb,
                "runs": prompt_runs,
            }
        )

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
