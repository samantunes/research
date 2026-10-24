"""Retriever factory and utilities for GPT Researcher.

This module provides functions to instantiate and manage various
search retriever implementations.
"""

import logging
from importlib.metadata import entry_points
from typing import Any

logger = logging.getLogger(__name__)

#: Entry-point group that third-party packages use to register retrievers.
RETRIEVER_ENTRY_POINT_GROUP = "gpt_researcher.retrievers"


def get_retriever(retriever: str):
    """Get a retriever class by name.

    Args:
        retriever: The name of the retriever to get (e.g., 'google', 'tavily', 'duckduckgo').

    Returns:
        The retriever class if found, None otherwise.

    Supported retrievers:
        - google: Google Custom Search
        - searx: SearX search engine
        - searchapi: SearchAPI service
        - serpapi: SerpAPI service
        - serper: Serper API
        - duckduckgo: DuckDuckGo search
        - bing: Bing search
        - brave: Brave Search API
        - arxiv: arXiv academic search
        - tavily: Tavily search API
        - exa: Exa search
        - crw: fastCRW search (Firecrawl-compatible web scraper)
        - semantic_scholar: Semantic Scholar academic search
        - pubmed_central: PubMed Central medical literature
        - openalex: OpenAlex scholarly works catalog
        - custom: Custom user-defined retriever
        - mcp: Model Context Protocol retriever
        - xquik: Xquik X/Twitter search
        - getxapi: GetXAPI X/Twitter search

    Any other name is looked up among installed plugins registered under the
    ``gpt_researcher.retrievers`` entry-point group. Built-in names always win.
    """
    match retriever:
        case "google":
            from gpt_researcher.retrievers import GoogleSearch

            return GoogleSearch
        case "searx":
            from gpt_researcher.retrievers import SearxSearch

            return SearxSearch
        case "searchapi":
            from gpt_researcher.retrievers import SearchApiSearch

            return SearchApiSearch
        case "serpapi":
            from gpt_researcher.retrievers import SerpApiSearch

            return SerpApiSearch
        case "serper":
            from gpt_researcher.retrievers import SerperSearch

            return SerperSearch
        case "duckduckgo":
            from gpt_researcher.retrievers import Duckduckgo

            return Duckduckgo
        case "bing":
            from gpt_researcher.retrievers import BingSearch

            return BingSearch
        case "brave":
            from gpt_researcher.retrievers import BraveSearch

            return BraveSearch
        case "bocha":
            from gpt_researcher.retrievers import BoChaSearch

            return BoChaSearch
        case "arxiv":
            from gpt_researcher.retrievers import ArxivSearch

            return ArxivSearch
        case "tavily":
            from gpt_researcher.retrievers import TavilySearch

            return TavilySearch
        case "groundroute":
            from gpt_researcher.retrievers import GroundRouteSearch

            return GroundRouteSearch
        case "exa":
            from gpt_researcher.retrievers import ExaSearch

            return ExaSearch
        case "crw":
            from gpt_researcher.retrievers import CRWRetriever

            return CRWRetriever
        case "semantic_scholar":
            from gpt_researcher.retrievers import SemanticScholarSearch

            return SemanticScholarSearch
        case "pubmed_central":
            from gpt_researcher.retrievers import PubMedCentralSearch

            return PubMedCentralSearch
        case "custom":
            from gpt_researcher.retrievers import CustomRetriever

            return CustomRetriever
        case "mcp":
            from gpt_researcher.retrievers import MCPRetriever

            return MCPRetriever
        case "xquik":
            from gpt_researcher.retrievers import XquikSearch

            return XquikSearch
        case "openalex":
            from gpt_researcher.retrievers import OpenAlexSearch

            return OpenAlexSearch
        case "getxapi":
            from gpt_researcher.retrievers import GetXAPISearch

            return GetXAPISearch

        case _:
            return _load_plugin_retriever(retriever)


def _load_plugin_retriever(name: str):
    """Load a retriever class that an installed package registered by name."""
    for entry_point in entry_points(group=RETRIEVER_ENTRY_POINT_GROUP, name=name):
        try:
            return entry_point.load()
        except Exception as exc:
            logger.warning(f"Failed to load retriever plugin '{name}' ({entry_point.value}): {exc}")
            return None
    return None


def get_retrievers(headers: dict[str, str], cfg):
    """
    Determine which retriever(s) to use based on headers, config, or default.

    Args:
        headers (dict): The headers dictionary
        cfg: The configuration object

    Returns:
        list: A list of retriever classes to be used for searching.
    """
    # Check headers first for multiple retrievers
    if headers.get("retrievers"):
        retrievers = headers.get("retrievers").split(",")
    # If not found, check headers for a single retriever
    elif headers.get("retriever"):
        retrievers = [headers.get("retriever")]
    # If not in headers, check config for multiple retrievers
    elif cfg.retrievers:
        # Handle both list and string formats for config retrievers
        if isinstance(cfg.retrievers, str):
            retrievers = cfg.retrievers.split(",")
        else:
            retrievers = cfg.retrievers
    # If not found, check config for a single retriever
    elif cfg.retriever:
        retrievers = [cfg.retriever]
    # If still not set, use default retriever
    else:
        retrievers = [get_default_retriever().__name__]

    # Strip whitespace from each retriever name so comma-separated lists with
    # spaces (e.g. "tavily, exa" from a header or config) resolve correctly
    # instead of silently falling back to the default retriever.
    retrievers = [r.strip() for r in retrievers if r and r.strip()]

    if not retrievers:
        return [get_default_retriever()]

    # Convert retriever names to actual retriever classes
    # Use get_default_retriever() as a fallback for any invalid retriever names
    retriever_classes = [get_retriever(r) or get_default_retriever() for r in retrievers]
    
    return retriever_classes


def get_default_retriever():
    """Get the default retriever class.

    Returns:
        The TavilySearch retriever class as the default search provider.
    """
    from gpt_researcher.retrievers import TavilySearch

    return TavilySearch


DEFAULT_EXCLUDE_DOMAINS = [
    "gitnux.com",
    "devgex.com",
    "reddit.com",
    "quora.com",
    "medium.com",
    "skillsdirectory.com",
    "coursehero.com",
    "scribd.com",
]

LOW_AUTHORITY_PATTERNS = [
    "discourse.",
    "skills-directory",
    "skillsdirectory",
    "skill.md",
]

HIGH_AUTHORITY_DOMAINS = [
    "arxiv.org",
    "dl.acm.org",
    "ieeexplore.ieee.org",
    "ntrs.nasa.gov",
    "standards.nasa.gov",
    "asme.org",
    "osti.gov",
    "par.nsf.gov",
    "joss.theoj.org",
    "springer.com",
    "wiley.com",
    "readthedocs.io",
    "github.com",
]


def is_low_authority_url(url: str, exclude_domains: list[str] | None = None) -> bool:
    """Check if a URL is from a low-authority noise domain, forum, or prompt directory.

    Filters:
    - Configured / default domain blocklist (e.g. reddit.com, gitnux.com, quora.com, etc.)
    - Wildcard / substring matches: forum URLs with 'discourse.', 'skills-directory', 'SKILL.md'
    """
    if not isinstance(url, str) or not url.strip():
        return True

    url_lower = url.strip().lower()

    # Substring / pattern filters
    for pattern in LOW_AUTHORITY_PATTERNS:
        if pattern.lower() in url_lower:
            return True

    # Parse hostname
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc.lower().split(":")[0]
    if not domain and "/" not in url:
        domain = url_lower.split("/")[0]

    if not isinstance(exclude_domains, (list, tuple, set)):
        blocked_domains = DEFAULT_EXCLUDE_DOMAINS
    else:
        blocked_domains = list(exclude_domains)

    all_excluded = set(d.lower().strip() for d in blocked_domains if isinstance(d, str) and d.strip())
    all_excluded.update(d.lower().strip() for d in DEFAULT_EXCLUDE_DOMAINS)

    for ex in all_excluded:
        if not ex:
            continue
        clean_ex = ex.lstrip("*.")
        if domain == clean_ex or domain.endswith("." + clean_ex) or clean_ex in domain:
            return True
        if "/" in ex and ex in url_lower:
            return True

    return False


def filter_low_authority_urls(
    search_results: list[dict | str] | set[str],
    exclude_domains: list[str] | None = None,
) -> list:
    """Filter out low-authority noise sources before scraping.

    Accepts a list or set of URLs (strings) or search result dicts (containing 'href' or 'url').
    Returns the filtered list maintaining order.
    """
    if not search_results:
        return []

    filtered = []
    for item in search_results:
        if isinstance(item, str):
            if not is_low_authority_url(item, exclude_domains):
                filtered.append(item)
        elif isinstance(item, dict):
            url = item.get("href") or item.get("url") or ""
            if url and not is_low_authority_url(url, exclude_domains):
                filtered.append(item)
        else:
            url = getattr(item, "url", None) or getattr(item, "metadata", {}).get("source", "")
            if url and not is_low_authority_url(url, exclude_domains):
                filtered.append(item)
    return filtered


def get_source_authority_score(item: Any) -> int:
    """Compute authority tier score for a URL, search result dict, or Document.

    Tier 1 (High Authority - 100):
      arxiv.org, dl.acm.org, ieeexplore.ieee.org, ntrs.nasa.gov, standards.nasa.gov,
      asme.org, osti.gov, par.nsf.gov, joss.theoj.org, springer.com, wiley.com,
      readthedocs.io, github.com
    Tier 2 (Reputable Academic / Standards / Lab - 50):
      .edu, .gov, doi.org, nature.com, sciencedirect.com, acm.org, ieee.org,
      nasa.gov, iso.org, nih.gov
    Tier 3 (Standard Web - 10):
      Other legitimate domains
    Tier 0 (Low Authority / Blocklisted - 0):
      Filtered / blocklisted domains
    """
    if isinstance(item, str):
        url = item
    elif isinstance(item, dict):
        url = item.get("href") or item.get("url") or item.get("source") or ""
    elif hasattr(item, "metadata") and isinstance(item.metadata, dict):
        url = item.metadata.get("source") or item.metadata.get("url") or ""
    else:
        url = getattr(item, "url", "")

    if not url:
        return 10

    if is_low_authority_url(url):
        return 0

    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc.lower().split(":")[0]

    for high_dom in HIGH_AUTHORITY_DOMAINS:
        clean_high = high_dom.lower().strip()
        if domain == clean_high or domain.endswith("." + clean_high):
            return 100

    tier2_patterns = [".edu", ".gov", "doi.org", "nature.com", "sciencedirect.com", "iso.org", "nih.gov"]
    for t2 in tier2_patterns:
        if domain.endswith(t2) or t2 in domain:
            return 50

    return 10


def rerank_sources_by_authority(sources: list) -> list:
    """Stable re-ranking of sources by authority tier score in descending order.

    Boosts high-authority scientific/engineering domains to the top of the context window.
    """
    if not sources or not isinstance(sources, list):
        return sources
    return sorted(sources, key=get_source_authority_score, reverse=True)

