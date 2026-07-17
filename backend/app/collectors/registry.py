from typing import Any

from app.collectors.base import BaseCollector


class CollectorRegistry:
    """Registry of all collectors."""

    def __init__(self):
        self._collectors: list[BaseCollector] = []

    def register(self, collector: BaseCollector) -> None:
        self._collectors.append(collector)

    def all_collectors(self) -> list[BaseCollector]:
        return self._collectors.copy()

    async def available(self) -> list[BaseCollector]:
        result = []
        for collector in self._collectors:
            try:
                if await collector.is_available():
                    result.append(collector)
            except Exception:  # noqa: BLE001
                pass
        return result


registry = CollectorRegistry()


def register(collector_cls: type[BaseCollector]) -> type[BaseCollector]:
    registry.register(collector_cls())
    return collector_cls
