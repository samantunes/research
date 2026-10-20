"""Routing: free tier first, then commercial providers within budget and quota."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid

from enki_research.core.cache import ResultCache, cache_key
from enki_research.core.db import Database
from enki_research.core.normalize import fuse
from enki_research.core.quota import QuotaManager
from enki_research.core.settings import Settings
from enki_research.models import ProviderReport, SearchRequest, SearchResponse, SearchResult
from enki_research.providers.base import Provider, ProviderOutput

log = logging.getLogger("enki_research.router")

# Free providers queried in parallel, by category and depth.
FREE_PLAN: dict[str, dict[str, list[str]]] = {
    "general":    {"quick": ["searxng"], "standard": ["searxng"], "deep": ["searxng"]},
    "commercial": {"quick": ["searxng"], "standard": ["searxng"], "deep": ["searxng"]},
    "academic": {
        "quick": ["searxng", "openalex"],
        "standard": ["searxng", "openalex", "semantic_scholar"],
        "deep": ["searxng", "openalex", "semantic_scholar", "arxiv", "crossref"],
    },
    "code": {"quick": ["searxng"], "standard": ["searxng", "github"], "deep": ["searxng", "github"]},
    "news": {"quick": ["searxng"], "standard": ["searxng"], "deep": ["searxng"]},
}

# Commercial providers, in order of preference, by category.
PAID_ORDER: dict[str, list[str]] = {
    "general": ["brave", "tavily", "exa"],
    "commercial": ["tavily", "brave", "exa"],
    "academic": ["exa", "tavily"],
    "code": ["exa", "tavily"],
    "news": ["tavily", "brave"],
}
# depth=deep always tries one semantic/agentic provider first when budget allows.
DEEP_PAID_FIRST: dict[str, str] = {
    "general": "exa", "commercial": "tavily", "academic": "exa", "code": "exa", "news": "tavily",
}


class Router:
    def __init__(self, settings: Settings, providers: dict[str, Provider], db: Database,
                 quota: QuotaManager, cache: ResultCache):
        self.settings = settings
        self.providers = providers
        self.db = db
        self.quota = quota
        self.cache = cache

    # --- planning ----------------------------------------------------------------
    def plan(self, req: SearchRequest) -> tuple[list[str], list[str]]:
        """Return (free providers to query now, paid providers in fallback order)."""
        if req.providers:
            names = [p for p in req.providers if p in self.providers]
            free = [p for p in names if self.providers[p].is_free]
            paid = [p for p in names if not self.providers[p].is_free]
            return free, paid
        free = FREE_PLAN[req.category][req.depth]
        paid = list(PAID_ORDER[req.category])
        if req.depth == "deep":
            first = DEEP_PAID_FIRST[req.category]
            paid = [first] + [p for p in paid if p != first]
        return free, paid

    # --- execution ---------------------------------------------------------------
    async def _call(self, name: str, req: SearchRequest, limit: int) -> tuple[ProviderReport, list[SearchResult]]:
        prov = self.providers[name]
        t0 = time.monotonic()
        try:
            out: ProviderOutput = await asyncio.wait_for(
                prov.search(req, limit), timeout=self.settings.provider_timeout
            )
        except Exception as e:  # noqa: BLE001 - any provider failure must degrade gracefully
            detail = f"{type(e).__name__}: {e}"[:300] if str(e) else type(e).__name__
            log.warning("provider %s failed: %s", name, detail)
            return ProviderReport(name=name, status="error", latency_ms=int((time.monotonic() - t0) * 1000),
                                  detail=detail), []
        report = ProviderReport(
            name=name, status="ok", latency_ms=int((time.monotonic() - t0) * 1000),
            count=len(out.results), unresponsive_engines=out.unresponsive_engines,
        )
        if out.reported_cost is not None:
            report.units = out.reported_cost
        return report, out.results

    async def search(self, req: SearchRequest) -> SearchResponse:
        t0 = time.monotonic()
        request_id = uuid.uuid4().hex[:16]
        key = cache_key(req)

        if not req.no_cache:
            cached = self.cache.get(key)
            if cached is not None:
                cached.request_id = request_id
                cached.cache_hit = True
                cached.paid_calls = 0
                cached.latency_ms = int((time.monotonic() - t0) * 1000)
                cached.providers_used = [ProviderReport(name=p.name, status="cached", count=p.count)
                                         for p in cached.providers_used if p.status == "ok"]
                self._audit(req, cached)
                return cached

        free, paid = self.plan(req)
        limit = max(req.max_results, 10)
        reports: list[ProviderReport] = []
        lists: dict[str, list[SearchResult]] = {}

        runnable = []
        for name in free:
            if self.providers[name].enabled():
                runnable.append(name)
            else:
                reports.append(ProviderReport(name=name, status="skipped", detail="disabled"))
        for report, results in await asyncio.gather(*(self._call(n, req, limit) for n in runnable)):
            reports.append(report)
            if results:
                lists[report.name] = results

        budget = req.paid_budget()
        paid_calls = 0
        target = min(req.max_results, self.settings.min_results)
        force_one = req.depth == "deep" or bool(req.providers and paid)
        for name in paid:
            if paid_calls >= budget:
                break
            unique = len(fuse(lists, 10_000))
            if unique >= target and not (force_one and paid_calls == 0):
                break
            prov = self.providers[name]
            if not prov.enabled():
                reports.append(ProviderReport(name=name, status="skipped", detail="disabled or no API key"))
                continue
            units = prov.cost_units(req)
            if not self.quota.try_reserve(name, units):
                st = self.quota.status(name)
                reports.append(ProviderReport(
                    name=name, status="skipped",
                    detail=f"free quota guard: {st.effective:g}/{st.cap:g} used this period"))
                continue
            paid_calls += 1
            report, results = await self._call(name, req, limit)
            if report.units:  # provider-reported cost
                self.quota.adjust(name, units, report.units)
            else:
                report.units = units
            reports.append(report)
            if results:
                lists[name] = results

        merged = fuse(lists, req.max_results)
        resp = SearchResponse(
            request_id=request_id, query=req.query, category=req.category, results=merged,
            providers_used=reports, paid_calls=paid_calls, cache_hit=False,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
        if merged and any(r.status == "ok" for r in reports):
            self.cache.put(key, resp, self.settings.ttl_for(req.category))
        self._audit(req, resp)
        return resp

    def _audit(self, req: SearchRequest, resp: SearchResponse) -> None:
        try:
            self.db.log_request(
                request_id=resp.request_id, query=req.query, category=req.category, depth=req.depth,
                cache_hit=resp.cache_hit, paid_calls=resp.paid_calls, n_results=len(resp.results),
                latency_ms=resp.latency_ms,
                provider_reports=[p.model_dump() for p in resp.providers_used],
            )
            if not resp.cache_hit:
                self.db.record_seen([r.model_dump() for r in resp.results])
        except Exception:  # noqa: BLE001 - auditing must never break a search
            log.exception("audit logging failed")
        log.info(
            "search id=%s cat=%s depth=%s cache=%s paid=%d results=%d ms=%d providers=%s",
            resp.request_id, req.category, req.depth, resp.cache_hit, resp.paid_calls, len(resp.results),
            resp.latency_ms, ",".join(f"{p.name}:{p.status}" for p in resp.providers_used),
        )
