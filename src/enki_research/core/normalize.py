"""URL canonicalisation, deduplication and rank fusion."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from enki_research.models import SearchResult

_TRACKING_PARAMS = {
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid", "yclid",
    "ref", "ref_src", "ref_url", "spm", "_hsenc", "_hsmi", "si", "source", "feature",
}
_ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/[0-9]{7})")
_DOI_RE = re.compile(r"(?:dx\.)?doi\.org/(10\.\d{4,9}/\S+)", re.I)

RRF_K = 60


def canonical_url(url: str) -> str:
    """Return a stable key for a URL (not necessarily a fetchable URL)."""
    raw = url.strip()
    m = _ARXIV_RE.search(raw)
    if m:
        return f"arxiv:{m.group(1)}"
    m = _DOI_RE.search(raw)
    if m:
        return f"doi:{m.group(1).lower().rstrip('/')}"
    try:
        parts = urlsplit(raw)
    except ValueError:
        return raw.lower()
    if not parts.scheme or not parts.netloc:
        return raw.lower()
    host = parts.hostname or ""
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m.") and host.count(".") >= 2:
        host = host[2:]
    port = f":{parts.port}" if parts.port and parts.port not in (80, 443) else ""
    path = parts.path or "/"
    path = re.sub(r"/{2,}", "/", path)
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    query.sort()
    # Scheme is dropped on purpose: http/https duplicates collapse.
    return urlunsplit(("", host + port, path, urlencode(query), "")).lstrip("/")


def fuse(result_lists: dict[str, list[SearchResult]], max_results: int) -> list[SearchResult]:
    """Deduplicate by canonical URL and merge rankings with Reciprocal Rank Fusion."""
    merged: dict[str, SearchResult] = {}
    for provider, results in result_lists.items():
        for rank, res in enumerate(results, start=1):
            key = res.canonical_url or canonical_url(res.url)
            contribution = 1.0 / (RRF_K + rank)
            if key not in merged:
                item = res.model_copy(deep=True)
                item.canonical_url = key
                item.providers = list(dict.fromkeys(res.providers or [provider]))
                item.rank_by_provider = {provider: rank}
                item.score = contribution
                merged[key] = item
                continue
            item = merged[key]
            item.score += contribution
            item.rank_by_provider.setdefault(provider, rank)
            for p in res.providers or [provider]:
                if p not in item.providers:
                    item.providers.append(p)
            if len(res.snippet) > len(item.snippet):
                item.snippet = res.snippet
            if not item.title and res.title:
                item.title = res.title
            if res.published_at and (not item.published_at or res.published_at < item.published_at):
                item.published_at = res.published_at
            for k, v in res.meta.items():
                item.meta.setdefault(k, v)
            # Prefer a human landing page over a PDF link for the same work.
            if item.url.lower().endswith(".pdf") and not res.url.lower().endswith(".pdf"):
                item.url = res.url
    ranked = sorted(merged.values(), key=lambda r: r.score, reverse=True)
    for r in ranked:
        r.score = round(r.score, 6)
    return ranked[:max_results]
