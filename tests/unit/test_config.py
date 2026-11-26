"""Unit tests for PRIME typed configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from prime.config import (
    ConfigError,
    EnvironmentMode,
    LanguageMode,
    MemoryProfile,
    load_config,
)


@pytest.mark.unit
def test_default_config_identity_and_safety(tmp_path: Path) -> None:
    cfg = load_config(
        env={
            "PRIME_DATA_DIR": str(tmp_path / "data"),
            "PRIME_LOG_DIR": str(tmp_path / "logs"),
        }
    )
    assert cfg.identity.app_name == "PRIME"
    assert cfg.identity.bundle_id == "com.mrhrafi3.prime"
    assert cfg.identity.owner == "MrhRafi3"
    assert cfg.ai.local_only is True
    assert cfg.ai.memory_profile == MemoryProfile.BALANCED
    assert cfg.ai.language_mode == LanguageMode.BANGLA_ENGLISH
    assert cfg.activation.push_to_talk_enabled is True
    assert cfg.activation.double_clap_enabled is False
    assert cfg.activation.wake_word_enabled is False
    assert cfg.activation.background_mic_enabled is False
    assert cfg.security.allow_arbitrary_shell is False


@pytest.mark.unit
def test_toml_and_env_override(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        """
environment = "production"

[ai]
memory_profile = "eco"
language_mode = "en"

[logging]
level = "WARNING"
""",
        encoding="utf-8",
    )
    cfg = load_config(
        config_path=cfg_file,
        env={
            "PRIME_LOG_LEVEL": "DEBUG",
            "PRIME_DATA_DIR": str(tmp_path / "data"),
            "PRIME_LOG_DIR": str(tmp_path / "logs"),
        },
    )
    assert cfg.environment == EnvironmentMode.PRODUCTION
    assert cfg.ai.memory_profile == MemoryProfile.ECO
    assert cfg.ai.max_context_tokens == 2048
    assert cfg.ai.language_mode == LanguageMode.ENGLISH
    assert cfg.logging.level == "DEBUG"


@pytest.mark.unit
@pytest.mark.parametrize(
    "toml_body",
    [
        "[ai]\nlocal_only = false\n",
        "[activation]\nwake_word_enabled = true\n",
        "[activation]\nbackground_mic_enabled = true\n",
        "[security]\nallow_arbitrary_shell = true\n",
        "[security]\nrequire_tier2_confirmation = false\n",
        "[logging]\nlevel = 'NOPE'\n",
        "[storage]\ndb_filename = '../escape.db'\n",
    ],
)
def test_invalid_or_unsafe_config_rejected(tmp_path: Path, toml_body: str) -> None:
    cfg_file = tmp_path / "bad.toml"
    cfg_file.write_text(toml_body, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(config_path=cfg_file, env={})
