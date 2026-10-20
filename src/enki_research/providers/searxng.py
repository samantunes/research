"""SearXNG (self-hosted metasearch)."""

from __future__ import annotations

from enki_research.models import SearchRequest, SearchResult
from enki_research.providers.base import Provider, ProviderOutput, truncate

CATEGORY_MAP = {
    "general": "general",
    "commercial": "general",
    "academic": "science",
    "code": "it",
    "news": "news",
}


def _time_range(days: int | None) -> str | None:
    if not days:
        return None
    if days <= 1:
        return "day"
    if days <= 7:
        return "week"
    if days <= 31:
        return "month"
    return "year"


class SearxngProvider(Provider):
    name = "searxng"
    concurrency = 6

    def enabled(self) -> bool:
        return self.settings.searxng_enabled and bool(self.settings.searxng_url)

    async def _search(self, req: SearchRequest, limit: int) -> ProviderOutput:
        q = req.query
        if req.domains:
            q += " " + " OR ".join(f"site:{d}" for d in req.domains[:3])
        params = {"q": q, "format": "json", "categories": CATEGORY_MAP[req.category], "pageno": 1}
        if req.lang and req.lang != "all":
            params["language"] = req.lang
        tr = _time_range(req.freshness_days)
        if tr:
            params["time_range"] = tr
        resp = await self.http.get(f"{self.settings.searxng_url.rstrip('/')}/search", params=params)
        self._check(resp)
        data = resp.json()
        results = []
        for item in data.get("results", [])[: max(limit * 2, limit)]:
            url = item.get("url")
            if not url:
                continue
            engines = item.get("engines") or [item.get("engine")]
            meta = {"engines": [e for e in engines if e]}
            if item.get("doi"):
                meta["doi"] = item["doi"]
            results.append(
                SearchResult(
                    title=item.get("title") or "",
                    url=url,
                    snippet=truncate(item.get("content")),
                    published_at=(item.get("publishedDate") or None),
                    providers=[self.name],
                    meta=meta,
                )
            )
        unresponsive = [f"{e[0]}: {e[1]}" if isinstance(e, list) else str(e)
                        for e in data.get("unresponsive_engines", [])]
        return ProviderOutput(results=results[:limit], unresponsive_engines=unresponsive)
