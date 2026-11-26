"""Loads PRIME's configurable external system prompt securely."""

from __future__ import annotations

from pathlib import Path

from prime.config.settings import LanguageMode

DEFAULT_PROMPT_PATH = Path(__file__).resolve().parent / "system_prompt.md"


def load_system_prompt(
    *,
    prompt_path: Path | None = None,
    language_mode: LanguageMode = LanguageMode.BANGLA_ENGLISH,
    notes: tuple[str, ...] = (),
) -> str:
    """Load system prompt from markdown file and append bounded runtime guidance."""
    target = prompt_path or DEFAULT_PROMPT_PATH
    base_text = target.read_text(encoding="utf-8").strip()

    lang_hint = (
        "Active language preference: Bangla and English (bn-en)."
        if language_mode == LanguageMode.BANGLA_ENGLISH
        else "Active language preference: English only (en)."
    )
    parts = [base_text, lang_hint]
    if notes:
        joined = "; ".join(n.strip() for n in notes if n.strip())
        if joined:
            parts.append(f"Relevant local user notes: {joined}")
    return "\n\n".join(parts)
