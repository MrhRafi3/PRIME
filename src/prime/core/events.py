"""In-process typed event bus and assistant lifecycle states."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AssistantState(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    SHUTTING_DOWN = "shutting_down"


@dataclass(frozen=True, slots=True)
class PrimeEvent:
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())


EventHandler = Callable[[PrimeEvent], None]


class EventBus:
    """Lightweight synchronous in-process pub/sub event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        if handler not in self._subscribers[topic]:
            self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        if handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)

    def publish(self, topic: str, payload: dict[str, Any] | None = None) -> PrimeEvent:
        event = PrimeEvent(topic=topic, payload=dict(payload or {}))
        for handler in list(self._subscribers.get(topic, ())):
            handler(event)
        return event
