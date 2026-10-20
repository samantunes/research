"""Provider registry."""

from __future__ import annotations

import httpx

from enki_research.core.settings import Settings
from enki_research.providers.academic import (
    ArxivProvider,
    CrossrefProvider,
    OpenAlexProvider,
    SemanticScholarProvider,
)
from enki_research.providers.base import Provider, ProviderError, ProviderOutput
from enki_research.providers.commercial import BraveProvider, ExaProvider, TavilyProvider
from enki_research.providers.github import GithubProvider
from enki_research.providers.searxng import SearxngProvider

PROVIDER_CLASSES: list[type[Provider]] = [
    SearxngProvider,
    OpenAlexProvider,
    ArxivProvider,
    SemanticScholarProvider,
    CrossrefProvider,
    GithubProvider,
    TavilyProvider,
    ExaProvider,
    BraveProvider,
]


def build_providers(settings: Settings, http: httpx.AsyncClient) -> dict[str, Provider]:
    return {cls.name: cls(settings, http) for cls in PROVIDER_CLASSES}


__all__ = ["Provider", "ProviderError", "ProviderOutput", "build_providers", "PROVIDER_CLASSES"]
