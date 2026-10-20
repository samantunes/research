"""Free scholarly APIs: OpenAlex, arXiv, Semantic Scholar, Crossref."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta

from enki_research.models import SearchRequest, SearchResult
from enki_research.providers.base import Provider, ProviderOutput, truncate


def _since(days: int | None) -> str | None:
    if not days:
        return None
    return (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")


def _abstract_from_inverted(index: dict | None) -> str:
    if not index:
        return ""
    positions: list[tuple[int, str]] = [(p, w) for w, ps in index.items() for p in ps]
    return " ".join(w for _, w in sorted(positions))


class OpenAlexProvider(Provider):
    name = "openalex"
    concurrency = 4

    def enabled(self) -> bool:
        return self.settings.openalex_enabled

    async def _search(self, req: SearchRequest, limit: int) -> ProviderOutput:
        params: dict[str, str | int] = {"search": req.query, "per-page": min(limit, 50), **self._mailto()}
        if self.settings.openalex_api_key:
            params["api_key"] = self.settings.openalex_api_key
        since = _since(req.freshness_days)
        if since:
            params["filter"] = f"from_publication_date:{since}"
        resp = await self.http.get("https://api.openalex.org/works", params=params)
        self._check(resp)
        results = []
        for w in resp.json().get("results", []):
            loc = w.get("primary_location") or {}
            doi = w.get("doi")
            url = doi or loc.get("landing_page_url") or w.get("id")
            if not url:
                continue
            results.append(SearchResult(
                title=w.get("display_name") or w.get("title") or "",
                url=url,
                snippet=truncate(_abstract_from_inverted(w.get("abstract_inverted_index"))),
                published_at=w.get("publication_date"),
                providers=[self.name],
                meta={
                    "doi": doi,
                    "cited_by": w.get("cited_by_count"),
                    "venue": ((loc.get("source") or {}).get("display_name")),
                    "authors": [a["author"]["display_name"] for a in (w.get("authorships") or [])[:6]
                                if a.get("author")],
                    "open_access_url": (w.get("open_access") or {}).get("oa_url"),
                    "type": w.get("type"),
                },
            ))
        return ProviderOutput(results=results)


_ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivProvider(Provider):
    name = "arxiv"
    # arXiv API terms: no more than one request every 3 seconds.
    concurrency = 1
    min_interval = 3.0

    def enabled(self) -> bool:
        return self.settings.arxiv_enabled

    async def _search(self, req: SearchRequest, limit: int) -> ProviderOutput:
        terms = re.sub(r"[^\w\s\-]", " ", req.query).split()
        search_query = " AND ".join(f"all:{t}" for t in terms[:12]) or f"all:{req.query}"
        params = {"search_query": search_query, "max_results": min(limit, 30), "sortBy": "relevance"}
        resp = await self.http.get("https://export.arxiv.org/api/query", params=params)
        self._check(resp)
        root = ET.fromstring(resp.text)
        since = _since(req.freshness_days)
        results = []
        for e in root.findall("a:entry", _ATOM):
            url = (e.findtext("a:id", default="", namespaces=_ATOM) or "").strip()
            if not url:
                continue
            published = (e.findtext("a:published", default="", namespaces=_ATOM) or "")[:10] or None
            if since and published and published < since:
                continue
            results.append(SearchResult(
                title=" ".join((e.findtext("a:title", default="", namespaces=_ATOM) or "").split()),
                url=url,
                snippet=truncate(e.findtext("a:summary", default="", namespaces=_ATOM)),
                published_at=published,
                providers=[self.name],
                meta={
                    "authors": [a.findtext("a:name", default="", namespaces=_ATOM)
                                for a in e.findall("a:author", _ATOM)][:6],
                    "doi": e.findtext("arxiv:doi", default=None, namespaces=_ATOM),
                    "primary_category": (e.find("arxiv:primary_category", _ATOM).attrib.get("term")
                                         if e.find("arxiv:primary_category", _ATOM) is not None else None),
                },
            ))
        return ProviderOutput(results=results)


class SemanticScholarProvider(Provider):
    name = "semantic_scholar"
    # Unauthenticated traffic shares a global pool; stay gentle.
    concurrency = 1
    min_interval = 1.0

    def enabled(self) -> bool:
        return self.settings.semantic_scholar_enabled

    async def _search(self, req: SearchRequest, limit: int) -> ProviderOutput:
        params: dict[str, str | int] = {
            "query": req.query,
            "limit": min(limit, 50),
            "fields": "title,url,abstract,year,publicationDate,externalIds,citationCount,authors,venue,openAccessPdf",
        }
        if req.freshness_days:
            params["publicationDateOrYear"] = f"{_since(req.freshness_days)}:"
        headers = {"x-api-key": self.settings.semantic_scholar_api_key} if self.settings.semantic_scholar_api_key else {}
        resp = await self.http.get("https://api.semanticscholar.org/graph/v1/paper/search",
                                   params=params, headers=headers)
        self._check(resp)
        results = []
        for p in resp.json().get("data", []) or []:
            ext = p.get("externalIds") or {}
            doi = ext.get("DOI")
            url = (f"https://arxiv.org/abs/{ext['ArXiv']}" if ext.get("ArXiv")
                   else f"https://doi.org/{doi}" if doi else p.get("url"))
            if not url:
                continue
            results.append(SearchResult(
                title=p.get("title") or "",
                url=url,
                snippet=truncate(p.get("abstract")),
                published_at=p.get("publicationDate") or (str(p["year"]) if p.get("year") else None),
                providers=[self.name],
                meta={
                    "doi": doi,
                    "cited_by": p.get("citationCount"),
                    "venue": p.get("venue"),
                    "authors": [a.get("name") for a in (p.get("authors") or [])[:6]],
                    "open_access_url": (p.get("openAccessPdf") or {}).get("url"),
                    "s2_url": p.get("url"),
                },
            ))
        return ProviderOutput(results=results)


_TAG_RE = re.compile(r"<[^>]+>")


class CrossrefProvider(Provider):
    name = "crossref"
    concurrency = 2

    def enabled(self) -> bool:
        return self.settings.crossref_enabled

    async def _search(self, req: SearchRequest, limit: int) -> ProviderOutput:
        params: dict[str, str | int] = {
            "query.bibliographic": req.query,
            "rows": min(limit, 40),
            "select": "DOI,title,URL,abstract,published,container-title,author,is-referenced-by-count,type",
            **self._mailto(),
        }
        since = _since(req.freshness_days)
        if since:
            params["filter"] = f"from-pub-date:{since}"
        resp = await self.http.get("https://api.crossref.org/works", params=params)
        self._check(resp)
        results = []
        for it in resp.json().get("message", {}).get("items", []):
            doi = it.get("DOI")
            url = f"https://doi.org/{doi}" if doi else it.get("URL")
            if not url:
                continue
            parts = ((it.get("published") or {}).get("date-parts") or [[None]])[0]
            date = "-".join(f"{x:02d}" if i else str(x) for i, x in enumerate(parts) if x) or None
            results.append(SearchResult(
                title=" ".join(it.get("title") or []),
                url=url,
                snippet=truncate(_TAG_RE.sub(" ", it.get("abstract") or "")),
                published_at=date,
                providers=[self.name],
                meta={
                    "doi": doi,
                    "cited_by": it.get("is-referenced-by-count"),
                    "venue": " ".join(it.get("container-title") or []) or None,
                    "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip()
                                for a in (it.get("author") or [])[:6]],
                    "type": it.get("type"),
                },
            ))
        return ProviderOutput(results=results)
