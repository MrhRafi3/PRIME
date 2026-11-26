"""Centralized, typed configuration with local file and env overrides."""

from __future__ import annotations

import json
import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from prime import APP_NAME, BUNDLE_ID, GITHUB_OWNER, __version__


class ConfigError(ValueError):
    """Raised when configuration values are invalid or violate safety invariants."""


class EnvironmentMode(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


class MemoryProfile(StrEnum):
    ECO = "eco"
    BALANCED = "balanced"
    HEAVY = "heavy"


class LanguageMode(StrEnum):
    BANGLA_ENGLISH = "bn-en"
    ENGLISH = "en"


class ActivationMethod(StrEnum):
    PUSH_TO_TALK = "push_to_talk"
    DOUBLE_CLAP = "double_clap"


_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
_PROFILE_CTX_DEFAULTS = {
    MemoryProfile.ECO: 2048,
    MemoryProfile.BALANCED: 4096,
    MemoryProfile.HEAVY: 2048,
}


def _default_app_support_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / APP_NAME


def _default_log_dir() -> Path:
    return Path.home() / "Library" / "Logs" / APP_NAME


def _parse_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigError(f"Invalid boolean for {field_name}: {value!r}")


def _parse_int(value: Any, field_name: str, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"Invalid integer for {field_name}: {value!r}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid integer for {field_name}: {value!r}") from exc
    if parsed < minimum:
        raise ConfigError(f"{field_name} must be >= {minimum}, got {parsed}")
    return parsed


def _parse_float(value: Any, field_name: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool):
        raise ConfigError(f"Invalid float for {field_name}: {value!r}")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid float for {field_name}: {value!r}") from exc
    if parsed < minimum:
        raise ConfigError(f"{field_name} must be >= {minimum}, got {parsed}")
    return parsed


@dataclass(frozen=True, slots=True)
class IdentityConfig:
    app_name: str = APP_NAME
    bundle_id: str = BUNDLE_ID
    owner: str = GITHUB_OWNER
    version: str = __version__


@dataclass(frozen=True, slots=True)
class StorageConfig:
    data_dir: Path = field(default_factory=_default_app_support_dir)
    log_dir: Path = field(default_factory=_default_log_dir)
    config_path: Path = field(default_factory=lambda: _default_app_support_dir() / "config.toml")
    db_filename: str = "prime_memory.db"

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_filename


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str = "INFO"
    max_bytes: int = 5 * 1024 * 1024
    backup_count: int = 5
    log_private_content: bool = False
    json_format: bool = True

    def __post_init__(self) -> None:
        normalized = self.level.upper()
        if normalized not in _VALID_LOG_LEVELS:
            raise ConfigError(f"Invalid log level: {self.level!r}")
        object.__setattr__(self, "level", normalized)
        if self.max_bytes < 1024:
            raise ConfigError("max_bytes must be >= 1024")
        if self.backup_count < 1:
            raise ConfigError("backup_count must be >= 1")


@dataclass(frozen=True, slots=True)
class ActivationConfig:
    push_to_talk_enabled: bool = True
    double_clap_enabled: bool = True
    wake_word_enabled: bool = False
    background_mic_enabled: bool = False
    clap_threshold: int = 2000
    clap_min_interval_s: float = 0.1
    clap_max_interval_s: float = 0.8

    def __post_init__(self) -> None:
        if self.wake_word_enabled:
            raise ConfigError("Wake-word activation is deferred and cannot be enabled in Phase 02.")
        if self.background_mic_enabled:
            raise ConfigError("Background microphone recording is disabled in Phase 02.")
        if self.clap_min_interval_s >= self.clap_max_interval_s:
            raise ConfigError("clap_min_interval_s must be < clap_max_interval_s")


@dataclass(frozen=True, slots=True)
class HardwareAIConfig:
    memory_profile: MemoryProfile = MemoryProfile.BALANCED
    language_mode: LanguageMode = LanguageMode.BANGLA_ENGLISH
    local_only: bool = True
    max_context_tokens: int = 4096
    idle_unload_seconds: int = 300

    def __post_init__(self) -> None:
        if not self.local_only:
            raise ConfigError("PRIME enforces 100% local inference; local_only must be True.")
        if self.max_context_tokens < 512 or self.max_context_tokens > 8192:
            raise ConfigError("max_context_tokens must be between 512 and 8192 for M1 8GB safety.")
        if self.idle_unload_seconds < 30:
            raise ConfigError("idle_unload_seconds must be >= 30")


@dataclass(frozen=True, slots=True)
class SecurityConfig:
    require_tier2_confirmation: bool = True
    sandbox_root: Path = field(default_factory=lambda: Path.home() / "Desktop")
    allowed_apps: tuple[str, ...] = ("Safari", "Google Chrome", "Finder", "Terminal", "Notes")
    allowed_url_schemes: tuple[str, ...] = ("https", "http")
    allow_network_plugins: bool = False
    allow_arbitrary_shell: bool = False

    def __post_init__(self) -> None:
        if self.allow_arbitrary_shell:
            raise ConfigError("Arbitrary shell execution is prohibited by PRIME security policy.")
        if not self.require_tier2_confirmation:
            raise ConfigError("Tier 2 confirmation cannot be globally disabled.")


@dataclass(frozen=True, slots=True)
class PrimeConfig:
    environment: EnvironmentMode = EnvironmentMode.DEVELOPMENT
    identity: IdentityConfig = field(default_factory=IdentityConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    activation: ActivationConfig = field(default_factory=ActivationConfig)
    ai: HardwareAIConfig = field(default_factory=HardwareAIConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a non-sensitive dictionary view of runtime configuration."""
        return {
            "environment": self.environment.value,
            "identity": {
                "app_name": self.identity.app_name,
                "bundle_id": self.identity.bundle_id,
                "owner": self.identity.owner,
                "version": self.identity.version,
            },
            "storage": {
                "data_dir": str(self.storage.data_dir),
                "log_dir": str(self.storage.log_dir),
                "config_path": str(self.storage.config_path),
                "db_filename": self.storage.db_filename,
            },
            "logging": {
                "level": self.logging.level,
                "max_bytes": self.logging.max_bytes,
                "backup_count": self.logging.backup_count,
                "log_private_content": self.logging.log_private_content,
                "json_format": self.logging.json_format,
            },
            "activation": {
                "push_to_talk_enabled": self.activation.push_to_talk_enabled,
                "double_clap_enabled": self.activation.double_clap_enabled,
                "wake_word_enabled": self.activation.wake_word_enabled,
                "background_mic_enabled": self.activation.background_mic_enabled,
            },
            "ai": {
                "memory_profile": self.ai.memory_profile.value,
                "language_mode": self.ai.language_mode.value,
                "local_only": self.ai.local_only,
                "max_context_tokens": self.ai.max_context_tokens,
                "idle_unload_seconds": self.ai.idle_unload_seconds,
            },
            "security": {
                "require_tier2_confirmation": self.security.require_tier2_confirmation,
                "sandbox_root": str(self.security.sandbox_root),
                "allowed_apps": list(self.security.allowed_apps),
                "allowed_url_schemes": list(self.security.allowed_url_schemes),
                "allow_network_plugins": self.security.allow_network_plugins,
                "allow_arbitrary_shell": self.security.allow_arbitrary_shell,
            },
        }


def _read_config_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    raw_bytes = path.read_bytes()
    if suffix == ".toml":
        data = tomllib.loads(raw_bytes.decode("utf-8"))
    elif suffix == ".json":
        data = json.loads(raw_bytes.decode("utf-8"))
    else:
        raise ConfigError(f"Unsupported configuration file format: {path.suffix}")
    if not isinstance(data, dict):
        raise ConfigError("Top-level configuration structure must be a mapping/table.")
    return data


def _merge_section(file_data: Mapping[str, Any], key: str) -> dict[str, Any]:
    val = file_data.get(key, {})
    if not isinstance(val, Mapping):
        raise ConfigError(f"Config section '{key}' must be a mapping.")
    return dict(val)


def load_config(
    config_path: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> PrimeConfig:
    """Load PRIME configuration from defaults, optional local file, and PRIME_* env vars."""
    environ = os.environ if env is None else env

    resolved_config_path = config_path
    if resolved_config_path is None and environ.get("PRIME_CONFIG_PATH"):
        resolved_config_path = Path(environ["PRIME_CONFIG_PATH"]).expanduser()
    elif resolved_config_path is None:
        default_toml = _default_app_support_dir() / "config.toml"
        if default_toml.exists():
            resolved_config_path = default_toml

    file_data: dict[str, Any] = {}
    if resolved_config_path is not None:
        if not resolved_config_path.exists():
            raise ConfigError(f"Configuration file not found: {resolved_config_path}")
        file_data = _read_config_file(resolved_config_path)

    env_str = str(environ.get("PRIME_ENVIRONMENT") or file_data.get("environment") or "development")
    try:
        environment = EnvironmentMode(env_str.strip().lower())
    except ValueError as exc:
        raise ConfigError(f"Invalid environment mode: {env_str!r}") from exc

    storage_sec = _merge_section(file_data, "storage")
    data_dir = Path(
        environ.get("PRIME_DATA_DIR") or storage_sec.get("data_dir") or _default_app_support_dir()
    ).expanduser()
    log_dir = Path(
        environ.get("PRIME_LOG_DIR") or storage_sec.get("log_dir") or _default_log_dir()
    ).expanduser()
    db_filename = str(storage_sec.get("db_filename", "prime_memory.db")).strip()
    if not db_filename or "/" in db_filename or "\\" in db_filename or ".." in db_filename:
        raise ConfigError(f"Invalid db_filename: {db_filename!r}")
    storage = StorageConfig(
        data_dir=data_dir,
        log_dir=log_dir,
        config_path=resolved_config_path or (data_dir / "config.toml"),
        db_filename=db_filename,
    )

    log_sec = _merge_section(file_data, "logging")
    log_level = str(environ.get("PRIME_LOG_LEVEL") or log_sec.get("level") or "INFO")
    log_private_raw = environ.get(
        "PRIME_LOG_PRIVATE_CONTENT", log_sec.get("log_private_content", False)
    )
    logging_cfg = LoggingConfig(
        level=log_level,
        max_bytes=_parse_int(log_sec.get("max_bytes", 5 * 1024 * 1024), "logging.max_bytes", 1024),
        backup_count=_parse_int(log_sec.get("backup_count", 5), "logging.backup_count", 1),
        log_private_content=_parse_bool(log_private_raw, "logging.log_private_content"),
        json_format=_parse_bool(log_sec.get("json_format", True), "logging.json_format"),
    )

    act_sec = _merge_section(file_data, "activation")
    activation = ActivationConfig(
        push_to_talk_enabled=_parse_bool(
            act_sec.get("push_to_talk_enabled", True), "activation.push_to_talk_enabled"
        ),
        double_clap_enabled=_parse_bool(
            act_sec.get("double_clap_enabled", True), "activation.double_clap_enabled"
        ),
        wake_word_enabled=_parse_bool(
            act_sec.get("wake_word_enabled", False), "activation.wake_word_enabled"
        ),
        background_mic_enabled=_parse_bool(
            act_sec.get("background_mic_enabled", False), "activation.background_mic_enabled"
        ),
        clap_threshold=_parse_int(act_sec.get("clap_threshold", 2000), "clap_threshold", 100),
        clap_min_interval_s=_parse_float(
            act_sec.get("clap_min_interval_s", 0.1), "clap_min_interval_s", 0.01
        ),
        clap_max_interval_s=_parse_float(
            act_sec.get("clap_max_interval_s", 0.8), "clap_max_interval_s", 0.05
        ),
    )

    ai_sec = _merge_section(file_data, "ai")
    profile_raw = str(
        environ.get("PRIME_MEMORY_PROFILE") or ai_sec.get("memory_profile") or "balanced"
    )
    try:
        profile = MemoryProfile(profile_raw.strip().lower())
    except ValueError as exc:
        raise ConfigError(f"Invalid memory profile: {profile_raw!r}") from exc

    lang_raw = str(environ.get("PRIME_LANGUAGE_MODE") or ai_sec.get("language_mode") or "bn-en")
    try:
        language = LanguageMode(lang_raw.strip().lower())
    except ValueError as exc:
        raise ConfigError(f"Invalid language mode: {lang_raw!r}") from exc

    default_ctx = _PROFILE_CTX_DEFAULTS[profile]
    ai_cfg = HardwareAIConfig(
        memory_profile=profile,
        language_mode=language,
        local_only=_parse_bool(ai_sec.get("local_only", True), "ai.local_only"),
        max_context_tokens=_parse_int(
            ai_sec.get("max_context_tokens", default_ctx), "ai.max_context_tokens", 512
        ),
        idle_unload_seconds=_parse_int(
            ai_sec.get("idle_unload_seconds", 300), "ai.idle_unload_seconds", 30
        ),
    )

    sec_sec = _merge_section(file_data, "security")
    allowed_apps_raw = sec_sec.get(
        "allowed_apps", ("Safari", "Google Chrome", "Finder", "Terminal", "Notes")
    )
    if not isinstance(allowed_apps_raw, (list, tuple)) or not all(
        isinstance(x, str) and x.strip() for x in allowed_apps_raw
    ):
        raise ConfigError("security.allowed_apps must be a list of non-empty strings.")
    allowed_schemes_raw = sec_sec.get("allowed_url_schemes", ("https", "http"))
    if not isinstance(allowed_schemes_raw, (list, tuple)) or not all(
        isinstance(x, str) and x.strip() for x in allowed_schemes_raw
    ):
        raise ConfigError("security.allowed_url_schemes must be a list of non-empty strings.")

    security = SecurityConfig(
        require_tier2_confirmation=_parse_bool(
            sec_sec.get("require_tier2_confirmation", True),
            "security.require_tier2_confirmation",
        ),
        sandbox_root=Path(sec_sec.get("sandbox_root") or (Path.home() / "Desktop")).expanduser(),
        allowed_apps=tuple(x.strip() for x in allowed_apps_raw),
        allowed_url_schemes=tuple(x.strip().lower() for x in allowed_schemes_raw),
        allow_network_plugins=_parse_bool(
            sec_sec.get("allow_network_plugins", False), "security.allow_network_plugins"
        ),
        allow_arbitrary_shell=_parse_bool(
            sec_sec.get("allow_arbitrary_shell", False), "security.allow_arbitrary_shell"
        ),
    )

    return PrimeConfig(
        environment=environment,
        identity=IdentityConfig(),
        storage=storage,
        logging=logging_cfg,
        activation=activation,
        ai=ai_cfg,
        security=security,
    )


def _toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def save_config_toml(config: PrimeConfig, path: Path | None = None) -> Path:
    """Persist non-sensitive PRIME configuration atomically to TOML (0700/0600)."""
    target = (path or config.storage.config_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)

    allowed_apps = ", ".join(_toml_quote(a) for a in config.security.allowed_apps)
    allowed_schemes = ", ".join(_toml_quote(s) for s in config.security.allowed_url_schemes)
    lines = [
        f"environment = {_toml_quote(config.environment.value)}",
        "",
        "[storage]",
        f"data_dir = {_toml_quote(str(config.storage.data_dir))}",
        f"log_dir = {_toml_quote(str(config.storage.log_dir))}",
        f"db_filename = {_toml_quote(config.storage.db_filename)}",
        "",
        "[logging]",
        f"level = {_toml_quote(config.logging.level)}",
        f"max_bytes = {config.logging.max_bytes}",
        f"backup_count = {config.logging.backup_count}",
        f"log_private_content = {'true' if config.logging.log_private_content else 'false'}",
        f"json_format = {'true' if config.logging.json_format else 'false'}",
        "",
        "[activation]",
        f"push_to_talk_enabled = {'true' if config.activation.push_to_talk_enabled else 'false'}",
        f"double_clap_enabled = {'true' if config.activation.double_clap_enabled else 'false'}",
        "wake_word_enabled = false",
        "background_mic_enabled = false",
        f"clap_threshold = {config.activation.clap_threshold}",
        f"clap_min_interval_s = {config.activation.clap_min_interval_s}",
        f"clap_max_interval_s = {config.activation.clap_max_interval_s}",
        "",
        "[ai]",
        f"memory_profile = {_toml_quote(config.ai.memory_profile.value)}",
        f"language_mode = {_toml_quote(config.ai.language_mode.value)}",
        "local_only = true",
        f"max_context_tokens = {config.ai.max_context_tokens}",
        f"idle_unload_seconds = {config.ai.idle_unload_seconds}",
        "",
        "[security]",
        "require_tier2_confirmation = true",
        f"sandbox_root = {_toml_quote(str(config.security.sandbox_root))}",
        f"allowed_apps = [{allowed_apps}]",
        f"allowed_url_schemes = [{allowed_schemes}]",
        f"allow_network_plugins = {'true' if config.security.allow_network_plugins else 'false'}",
        "allow_arbitrary_shell = false",
        "",
    ]
    tmp_path = target.with_suffix(".toml.tmp")
    tmp_path.write_text("\n".join(lines), encoding="utf-8")
    os.chmod(tmp_path, 0o600)
    tmp_path.replace(target)
    os.chmod(target, 0o600)
    return target
