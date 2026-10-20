"""Commercial search APIs, used only within their free monthly quotas.

Quota units:
* tavily: API credits (basic search = 1 credit)
* exa:    USD (the free tier is a monthly dollar credit)
* brave:  requests (the $5 monthly credit ~= 1,000 web searches)
"""

from __future__ import annotations

from enki_research.models import SearchRequest, SearchResult
from enki_research.providers.base import Provider, ProviderOutput, truncate


class TavilyProvider(Provider):
    name = "tavily"
    is_free = False
    concurrency = 3

    def enabled(self) -> bool:
        return self.settings.tavily_enabled and bool(self.settings.tavily_api_key)

    def cost_units(self, req: SearchRequest) -> float:
        return 1.0  # search_depth=basic is always used

    async def _search(self, req: SearchRequest, limit: int) -> ProviderOutput:
        body: dict = {
            "query": req.query,
            "max_results": min(limit, 20),
            "search_depth": "basic",
            "topic": "news" if req.category == "news" else "general",
            "include_answer": False,
            "include_raw_content": False,
        }
        if req.freshness_days:
            body["days"] = req.freshness_days
        if req.domains:
            body["include_domains"] = req.domains
        resp = await self.http.post(
            "https://api.tavily.com/search", json=body,
            headers={"Authorization": f"Bearer {self.settings.tavily_api_key}"},
        )
        self._check(resp)
        data = resp.json()
        results = [
            SearchResult(
                title=r.get("title") or "",
                url=r["url"],
                snippet=truncate(r.get("content")),
                published_at=r.get("published_date"),
                providers=[self.name],
                meta={"provider_score": r.get("score")},
            )
            for r in data.get("results", []) if r.get("url")
        ]
        return ProviderOutput(results=results)

    async def fetch_reported_usage(self) -> float | None:
        """Credits used in the current period according to Tavily (GET /usage)."""
        resp = await self.http.get(
            "https://api.tavily.com/usage",
            headers={"Authorization": f"Bearer {self.settings.tavily_api_key}"},
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        acct = data.get("account") or {}
        key = data.get("key") or {}
        values = [v for v in (acct.get("plan_usage"), key.get("usage")) if isinstance(v, int | float)]
        return float(max(values)) if values else None


class ExaProvider(Provider):
    name = "exa"
    is_free = False
    concurrency = 2
    _EST_COST_USD = 0.007  # conservative estimate per auto search (<=10 results)

    def enabled(self) -> bool:
        return self.settings.exa_enabled and bool(self.settings.exa_api_key)

    def cost_units(self, req: SearchRequest) -> float:
        return self._EST_COST_USD

    async def _search(self, req: SearchRequest, limit: int) -> ProviderOutput:
        body: dict = {"query": req.query, "numResults": min(limit, 10), "type": "auto",
                      "contents": {"highlights": {"numSentences": 2}}}
        category = {"academic": "research paper", "news": "news", "code": "github"}.get(req.category)
        if category:
            body["category"] = category
        if req.domains:
            body["includeDomains"] = req.domains
        resp = await self.http.post("https://api.exa.ai/search", json=body,
                                    headers={"x-api-key": self.settings.exa_api_key})
        self._check(resp)
        data = resp.json()
        results = [
            SearchResult(
                title=r.get("title") or "",
                url=r["url"],
                snippet=truncate(" ".join(r.get("highlights") or []) or r.get("text")),
                published_at=(r.get("publishedDate") or "")[:10] or None,
                providers=[self.name],
                meta={"author": r.get("author")},
            )
            for r in data.get("results", []) if r.get("url")
        ]
        cost = (data.get("costDollars") or {}).get("total")
        return ProviderOutput(results=results, reported_cost=float(cost) if cost is not None else None)


class BraveProvider(Provider):
    name = "brave"
    is_free = False
    concurrency = 1
    min_interval = 1.0  # free credit plans are limited to ~1 req/s

    def enabled(self) -> bool:
        return self.settings.brave_enabled and bool(self.settings.brave_api_key)

    def cost_units(self, req: SearchRequest) -> float:
        return 1.0

    async def _search(self, req: SearchRequest, limit: int) -> ProviderOutput:
        params: dict = {"q": req.query, "count": min(limit, 20)}
        if req.lang and req.lang != "all":
            params["search_lang"] = req.lang
        if req.freshness_days:
            d = req.freshness_days
            params["freshness"] = "pd" if d <= 1 else "pw" if d <= 7 else "pm" if d <= 31 else "py"
        resp = await self.http.get(
            "https://api.search.brave.com/res/v1/web/search", params=params,
            headers={"X-Subscription-Token": self.settings.brave_api_key, "Accept": "application/json"},
        )
        self._check(resp)
        web = (resp.json().get("web") or {}).get("results", [])
        results = [
            SearchResult(
                title=r.get("title") or "",
                url=r["url"],
                snippet=truncate(r.get("description")),
                published_at=r.get("page_age"),
                providers=[self.name],
                meta={"age": r.get("age")},
            )
            for r in web if r.get("url")
        ]
        return ProviderOutput(results=results)
