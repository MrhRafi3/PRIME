"""PRIME core application bootstrap, wiring, and graceful lifecycle management."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from prime.config.settings import PrimeConfig, load_config
from prime.core.events import AssistantState, EventBus
from prime.intelligence.context.assembler import ContextAssembler
from prime.intelligence.memory.store import MemoryStore
from prime.logging.logger import configure_logging, log_event
from prime.plugins.contracts import PluginRegistry
from prime.security.manager import SecurityManager
from prime.security.tiers import ConfirmationHandler
from prime.system.base import PlatformKind, SystemController
from prime.system.factory import create_system_controller


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


class PrimeApp:
    """Coordinates PRIME core modules with clean bootstrap and shutdown."""

    def __init__(
        self,
        config: PrimeConfig,
        *,
        confirmation_handler: ConfirmationHandler | None = None,
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
        self._schema_version = 0

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
