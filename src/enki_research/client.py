"""HTTP client for the Enki Research Gateway (sync + async).

Only depends on httpx and pydantic, so consumers (GPT Researcher, agents) do not
need the server extras.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from enki_research.models import SearchRequest, SearchResponse


class EnkiResearchError(RuntimeError):
    pass


def _env_config() -> tuple[str, str]:
    url = os.getenv("ENKI_RESEARCH_URL")
    key = os.getenv("ENKI_RESEARCH_API_KEY")
    if not url or not key:
        raise EnkiResearchError("ENKI_RESEARCH_URL and ENKI_RESEARCH_API_KEY must be set")
    return url.rstrip("/"), key


def _build_request(query: str, **kwargs: Any) -> dict[str, Any]:
    return SearchRequest(query=query, **{k: v for k, v in kwargs.items() if v is not None}).model_dump(
        exclude_none=True
    )


class EnkiResearchClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 45.0):
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), headers={"X-API-Key": api_key}, timeout=timeout
        )

    @classmethod
    def from_env(cls, timeout: float | None = None) -> EnkiResearchClient:
        url, key = _env_config()
        return cls(url, key, timeout or float(os.getenv("ENKI_RESEARCH_TIMEOUT", "45")))

    def search(self, query: str, **kwargs: Any) -> SearchResponse:
        resp = self._client.post("/search", json=_build_request(query, **kwargs))
        if resp.status_code != 200:
            raise EnkiResearchError(f"gateway returned {resp.status_code}: {resp.text[:300]}")
        return SearchResponse.model_validate(resp.json())

    def usage(self) -> dict[str, Any]:
        resp = self._client.get("/usage")
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> EnkiResearchClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncEnkiResearchClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 45.0):
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), headers={"X-API-Key": api_key}, timeout=timeout
        )

    @classmethod
    def from_env(cls, timeout: float | None = None) -> AsyncEnkiResearchClient:
        url, key = _env_config()
        return cls(url, key, timeout or float(os.getenv("ENKI_RESEARCH_TIMEOUT", "45")))

    async def search(self, query: str, **kwargs: Any) -> SearchResponse:
        resp = await self._client.post("/search", json=_build_request(query, **kwargs))
        if resp.status_code != 200:
            raise EnkiResearchError(f"gateway returned {resp.status_code}: {resp.text[:300]}")
        return SearchResponse.model_validate(resp.json())

    async def usage(self) -> dict[str, Any]:
        resp = await self._client.get("/usage")
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncEnkiResearchClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
