"""GPT Researcher retrievers backed by the Enki Research Gateway.

Registered through the ``gpt_researcher.retrievers`` entry point group, so
GPT Researcher picks them up with e.g. ``RETRIEVER=enki,enki_academic`` without
any change to its source code.

Environment:
    ENKI_RESEARCH_URL        e.g. http://enki-research-gateway:8000
    ENKI_RESEARCH_API_KEY    one of the gateway's ENKI_API_KEYS
    ENKI_RESEARCH_DEPTH      quick | standard | deep          (default: standard)
    ENKI_RESEARCH_MAX_PAID   commercial calls per sub-query   (default: 1 for enki, 0 for the others)
    ENKI_RESEARCH_LANG       pt | en | all                    (default: all)
"""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar

from enki_research.client import EnkiResearchClient

logger = logging.getLogger(__name__)

_client: EnkiResearchClient | None = None


def _get_client() -> EnkiResearchClient:
    global _client
    if _client is None:
        _client = EnkiResearchClient.from_env()
    return _client


class EnkiSearch:
    """General web search (SearXNG first, commercial APIs as budgeted fallback)."""

    category: ClassVar[str] = "general"
    default_max_paid: ClassVar[int] = 1
    # The gateway returns snippets, not page text: GPT Researcher must scrape the URLs.
    requires_scraping: ClassVar[bool] = True

    def __init__(self, query: str, query_domains: list[str] | None = None, **_: Any):
        self.query = query
        self.query_domains = query_domains or None

    def search(self, max_results: int = 10) -> list[dict[str, str]]:
        env_key = f"ENKI_RESEARCH_MAX_PAID_{self.category.upper()}"
        max_paid = int(os.getenv(env_key, os.getenv("ENKI_RESEARCH_MAX_PAID", str(self.default_max_paid)))
                       if self.category == "general" else os.getenv(env_key, str(self.default_max_paid)))
        try:
            resp = _get_client().search(
                self.query,
                category=self.category,
                depth=os.getenv("ENKI_RESEARCH_DEPTH", "standard"),
                lang=os.getenv("ENKI_RESEARCH_LANG", "all"),
                max_results=max(1, min(int(max_results), 50)),
                max_paid_calls=max_paid,
                domains=self.query_domains,
            )
        except Exception as e:  # noqa: BLE001 - never break the research pipeline
            logger.warning("enki-research search failed for %r: %s", self.query, e)
            return []
        return [{"href": r.url, "title": r.title, "body": r.snippet} for r in resp.results]


class EnkiAcademicSearch(EnkiSearch):
    """Scholarly sources: SearXNG science + OpenAlex + Semantic Scholar (+ arXiv/Crossref when deep)."""

    category = "academic"
    default_max_paid = 0


class EnkiCodeSearch(EnkiSearch):
    """Code and technical sources: SearXNG it + GitHub repositories."""

    category = "code"
    default_max_paid = 0


class EnkiNewsSearch(EnkiSearch):
    """Recent news via SearXNG news engines."""

    category = "news"
    default_max_paid = 0
