from abc import ABC, abstractmethod
from typing import Any


class CollectorResult:
    """Result returned by a collector."""

    def __init__(
        self,
        source: str,
        success: bool,
        data: list[dict[str, Any]] | dict[str, Any] | None = None,
        error: str | None = None,
    ):
        self.source = source
        self.success = success
        self.data = data or []
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


class BaseCollector(ABC):
    """Abstract base class for all data collectors."""

    name: str = ""

    @abstractmethod
    async def is_available(self) -> bool:
        """Return True if the collector can run (e.g. API key present)."""
        ...

    @abstractmethod
    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        """Return a list of candidate dicts discovered for the destination."""
        ...

    @abstractmethod
    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        """Return enriched details for a single candidate."""
        ...
