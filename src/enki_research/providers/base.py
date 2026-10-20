"""Provider contract."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from enki_research.core.normalize import canonical_url
from enki_research.core.settings import Settings
from enki_research.models import SearchRequest, SearchResult


@dataclass
class ProviderOutput:
    results: list[SearchResult]
    unresponsive_engines: list[str] = field(default_factory=list)
    # Actual cost reported by the provider (same unit as the quota limit), when known.
    reported_cost: float | None = None


class ProviderError(RuntimeError):
    pass


class Provider(ABC):
    name: str = ""
    is_free: bool = True
    # Max concurrent calls and minimum seconds between call starts (politeness / rate limits).
    concurrency: int = 4
    min_interval: float = 0.0

    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        self.settings = settings
        self.http = http
        self._sem = asyncio.Semaphore(self.concurrency)
        self._interval_lock = asyncio.Lock()
        self._last_start = 0.0

    @abstractmethod
    def enabled(self) -> bool: ...

    def cost_units(self, req: SearchRequest) -> float:
        """Quota units a call consumes (paid providers only)."""
        return 0.0

    @abstractmethod
    async def _search(self, req: SearchRequest, limit: int) -> ProviderOutput: ...

    async def search(self, req: SearchRequest, limit: int) -> ProviderOutput:
        async with self._sem:
            if self.min_interval:
                async with self._interval_lock:
                    wait = self._last_start + self.min_interval - time.monotonic()
                    if wait > 0:
                        await asyncio.sleep(wait)
                    self._last_start = time.monotonic()
            out = await self._search(req, limit)
        for r in out.results:
            if not r.canonical_url:
                r.canonical_url = canonical_url(r.url)
            if not r.providers:
                r.providers = [self.name]
        return out

    # helpers ---------------------------------------------------------------
    def _mailto(self) -> dict[str, str]:
        return {"mailto": self.settings.contact_email} if self.settings.contact_email else {}

    @staticmethod
    def _check(resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:200]}")


def truncate(text: str | None, n: int = 600) -> str:
    if not text:
        return ""
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"
