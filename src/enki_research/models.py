"""Shared data model (used by the server, the client and the GPT Researcher plugin).

Only depends on pydantic so that the lightweight client install stays small.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Category = Literal["general", "commercial", "academic", "code", "news"]
Depth = Literal["quick", "standard", "deep"]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    category: Category = "general"
    lang: str = Field(default="all", max_length=10, description="ISO code (pt, en, ...) or 'all'")
    depth: Depth = "standard"
    max_results: int = Field(default=10, ge=1, le=50)
    # Ceiling of commercial (quota-consuming) calls for this request.
    # None -> default by depth (quick=0, standard=1, deep=2).
    max_paid_calls: int | None = Field(default=None, ge=0, le=5)
    # Explicit provider list overrides routing (quota rules still apply).
    providers: list[str] | None = None
    freshness_days: int | None = Field(default=None, ge=1, le=3650)
    domains: list[str] | None = None
    no_cache: bool = False

    def paid_budget(self) -> int:
        if self.max_paid_calls is not None:
            return self.max_paid_calls
        return {"quick": 0, "standard": 1, "deep": 2}[self.depth]


class SearchResult(BaseModel):
    title: str = ""
    url: str
    canonical_url: str = ""
    snippet: str = ""
    published_at: str | None = None
    providers: list[str] = Field(default_factory=list)
    score: float = 0.0
    rank_by_provider: dict[str, int] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class ProviderReport(BaseModel):
    name: str
    status: Literal["ok", "error", "skipped", "cached"] = "ok"
    latency_ms: int = 0
    count: int = 0
    units: float = 0.0
    detail: str | None = None
    unresponsive_engines: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    request_id: str
    query: str
    category: Category
    results: list[SearchResult]
    providers_used: list[ProviderReport]
    paid_calls: int = 0
    cache_hit: bool = False
    latency_ms: int = 0
