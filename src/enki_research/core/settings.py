"""Gateway configuration (environment variables prefixed with ENKI_ unless noted)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env(name: str, *aliases: str) -> AliasChoices:
    return AliasChoices(name, *aliases)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    # --- service -----------------------------------------------------------
    api_keys: str = Field(default="", validation_alias=_env("ENKI_API_KEYS"))
    db_path: str = Field(default="/data/enki_research.db", validation_alias=_env("ENKI_DB_PATH"))
    log_level: str = Field(default="INFO", validation_alias=_env("ENKI_LOG_LEVEL"))
    contact_email: str = Field(default="", validation_alias=_env("ENKI_CONTACT_EMAIL"))
    provider_timeout: float = Field(default=15.0, validation_alias=_env("ENKI_PROVIDER_TIMEOUT"))
    min_results: int = Field(default=5, validation_alias=_env("ENKI_MIN_RESULTS"))

    # --- quota ---------------------------------------------------------------
    quota_safety: float = Field(default=0.90, validation_alias=_env("ENKI_QUOTA_SAFETY"))

    # --- cache TTLs (seconds) ------------------------------------------------
    ttl_news: int = Field(default=6 * 3600, validation_alias=_env("ENKI_TTL_NEWS"))
    ttl_general: int = Field(default=3 * 86400, validation_alias=_env("ENKI_TTL_GENERAL"))
    ttl_code: int = Field(default=7 * 86400, validation_alias=_env("ENKI_TTL_CODE"))
    ttl_academic: int = Field(default=30 * 86400, validation_alias=_env("ENKI_TTL_ACADEMIC"))

    # --- free providers ------------------------------------------------------
    searxng_url: str = Field(default="http://enki-searxng:8080", validation_alias=_env("ENKI_SEARXNG_URL"))
    searxng_enabled: bool = Field(default=True, validation_alias=_env("SEARXNG_ENABLED"))
    openalex_enabled: bool = Field(default=True, validation_alias=_env("OPENALEX_ENABLED"))
    openalex_api_key: str = Field(default="", validation_alias=_env("OPENALEX_API_KEY"))
    arxiv_enabled: bool = Field(default=True, validation_alias=_env("ARXIV_ENABLED"))
    semantic_scholar_enabled: bool = Field(default=True, validation_alias=_env("SEMANTIC_SCHOLAR_ENABLED"))
    semantic_scholar_api_key: str = Field(default="", validation_alias=_env("SEMANTIC_SCHOLAR_API_KEY"))
    crossref_enabled: bool = Field(default=True, validation_alias=_env("CROSSREF_ENABLED"))
    github_enabled: bool = Field(default=True, validation_alias=_env("GITHUB_ENABLED"))
    github_token: str = Field(default="", validation_alias=_env("GITHUB_TOKEN"))

    # --- commercial providers (free quota only) ------------------------------
    # A paid provider is only used when *_ENABLED=true AND an API key is present.
    tavily_enabled: bool = Field(default=False, validation_alias=_env("TAVILY_ENABLED"))
    tavily_api_key: str = Field(default="", validation_alias=_env("TAVILY_API_KEY"))
    tavily_monthly_limit: float = Field(default=1000, validation_alias=_env("TAVILY_MONTHLY_LIMIT"))

    exa_enabled: bool = Field(default=False, validation_alias=_env("EXA_ENABLED"))
    exa_api_key: str = Field(default="", validation_alias=_env("EXA_API_KEY"))
    exa_monthly_limit_usd: float = Field(default=10.0, validation_alias=_env("EXA_MONTHLY_LIMIT_USD"))

    brave_enabled: bool = Field(default=False, validation_alias=_env("BRAVE_ENABLED"))
    brave_api_key: str = Field(default="", validation_alias=_env("BRAVE_API_KEY"))
    brave_monthly_limit: float = Field(default=1000, validation_alias=_env("BRAVE_MONTHLY_LIMIT"))

    @property
    def api_key_list(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    def ttl_for(self, category: str) -> int:
        return {
            "news": self.ttl_news,
            "code": self.ttl_code,
            "academic": self.ttl_academic,
        }.get(category, self.ttl_general)


@lru_cache
def get_settings() -> Settings:
    return Settings()
