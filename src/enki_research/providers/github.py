"""GitHub REST search API (repositories)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from enki_research.models import SearchRequest, SearchResult
from enki_research.providers.base import Provider, ProviderOutput, truncate


class GithubProvider(Provider):
    name = "github"
    # Search API: 10 req/min unauthenticated, 30 req/min with a token.
    concurrency = 2

    @property
    def min_interval(self) -> float:  # type: ignore[override]
        return 2.0 if self.settings.github_token else 6.0

    def enabled(self) -> bool:
        return self.settings.github_enabled

    async def _search(self, req: SearchRequest, limit: int) -> ProviderOutput:
        q = req.query
        if req.freshness_days:
            since = (datetime.now(UTC) - timedelta(days=req.freshness_days)).strftime("%Y-%m-%d")
            q += f" pushed:>={since}"
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        resp = await self.http.get(
            "https://api.github.com/search/repositories",
            params={"q": q, "per_page": min(limit, 30)},
            headers=headers,
        )
        self._check(resp)
        results = []
        for r in resp.json().get("items", []):
            desc = r.get("description") or ""
            topics = r.get("topics") or []
            results.append(SearchResult(
                title=r.get("full_name") or "",
                url=r["html_url"],
                snippet=truncate(desc + (f" [topics: {', '.join(topics[:8])}]" if topics else "")),
                published_at=(r.get("pushed_at") or "")[:10] or None,
                providers=[self.name],
                meta={
                    "stars": r.get("stargazers_count"),
                    "forks": r.get("forks_count"),
                    "language": r.get("language"),
                    "license": (r.get("license") or {}).get("spdx_id"),
                    "archived": r.get("archived"),
                    "topics": topics,
                },
            ))
        return ProviderOutput(results=results)
