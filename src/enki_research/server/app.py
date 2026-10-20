"""FastAPI application for the Research Gateway."""

from __future__ import annotations

import asyncio
import hmac
import logging
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request

from enki_research import __version__
from enki_research.core.cache import ResultCache
from enki_research.core.db import Database
from enki_research.core.quota import QuotaManager
from enki_research.core.router import Router
from enki_research.core.settings import Settings, get_settings
from enki_research.models import SearchRequest, SearchResponse
from enki_research.providers import build_providers
from enki_research.providers.commercial import TavilyProvider

log = logging.getLogger("enki_research")


def quota_limits(s: Settings) -> dict[str, float]:
    return {"tavily": s.tavily_monthly_limit, "exa": s.exa_monthly_limit_usd, "brave": s.brave_monthly_limit}


async def _reconcile_loop(app: FastAPI, interval: float = 3600) -> None:
    """Periodically import provider-reported usage (Tavily) and purge expired cache."""
    while True:
        try:
            tavily = app.state.providers.get("tavily")
            if isinstance(tavily, TavilyProvider) and tavily.enabled():
                reported = await tavily.fetch_reported_usage()
                if reported is not None:
                    app.state.quota.set_reported("tavily", reported)
            app.state.cache.purge_expired()
        except Exception:  # noqa: BLE001
            log.exception("reconcile loop failed")
        await asyncio.sleep(interval)


def create_app(settings: Settings | None = None, http: httpx.AsyncClient | None = None,
               start_background: bool = True) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(level=settings.log_level.upper(),
                            format="%(asctime)s %(levelname)s %(name)s %(message)s")
        if not settings.api_key_list:
            raise RuntimeError("ENKI_API_KEYS must contain at least one key")
        client = http or httpx.AsyncClient(
            timeout=httpx.Timeout(settings.provider_timeout, connect=5.0),
            headers={"User-Agent": f"enki-research/{__version__}"
                     + (f" (mailto:{settings.contact_email})" if settings.contact_email else "")},
            follow_redirects=True,
        )
        db = Database(settings.db_path)
        providers = build_providers(settings, client)
        quota = QuotaManager(db, quota_limits(settings), settings.quota_safety)
        cache = ResultCache(db)
        app.state.settings, app.state.db, app.state.providers = settings, db, providers
        app.state.quota, app.state.cache = quota, cache
        app.state.router = Router(settings, providers, db, quota, cache)
        task = asyncio.create_task(_reconcile_loop(app)) if start_background else None
        log.info("gateway ready; enabled providers: %s",
                 [n for n, p in providers.items() if p.enabled()])
        yield
        if task:
            task.cancel()
        if http is None:
            await client.aclose()
        db.close()

    app = FastAPI(title="Enki Research Gateway", version=__version__, lifespan=lifespan)

    def require_key(request: Request, x_api_key: Annotated[str | None, Header()] = None) -> None:
        keys = request.app.state.settings.api_key_list
        if not x_api_key or not any(hmac.compare_digest(x_api_key, k) for k in keys):
            raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")

    @app.get("/health")
    async def health(request: Request) -> dict:
        return {"status": "ok", "version": __version__}

    @app.post("/search", response_model=SearchResponse, dependencies=[Depends(require_key)])
    async def search(req: SearchRequest, request: Request) -> SearchResponse:
        return await request.app.state.router.search(req)

    @app.get("/providers", dependencies=[Depends(require_key)])
    async def providers(request: Request) -> list[dict]:
        return [{"name": n, "enabled": p.enabled(), "free": p.is_free}
                for n, p in request.app.state.providers.items()]

    @app.get("/usage", dependencies=[Depends(require_key)])
    async def usage(request: Request) -> dict:
        st = request.app.state
        quota = {}
        for name in st.quota.limits:
            s = st.quota.status(name)
            quota[name] = {"enabled": st.providers[name].enabled(), "period": s.period, "limit": s.limit,
                           "cap": s.cap, "used_local": s.used, "reported": s.reported,
                           "effective": s.effective, "remaining": s.remaining, "calls": s.calls}
        rows = st.db.query(
            "SELECT provider, status, COUNT(*) n, AVG(latency_ms) avg_ms, SUM(count) results"
            " FROM provider_calls WHERE ts > strftime('%s','now') - 86400 GROUP BY provider, status"
        )
        req_rows = st.db.query(
            "SELECT COUNT(*) n, SUM(cache_hit) hits, SUM(paid_calls) paid FROM requests"
            " WHERE ts > strftime('%s','now') - 86400"
        )
        return {
            "quota": quota,
            "last_24h": {
                "requests": dict(req_rows[0]) if req_rows else {},
                "providers": [dict(r) for r in rows],
            },
        }

    return app


def app_factory() -> FastAPI:
    return create_app()
