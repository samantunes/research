import time
import pytest
from enki_research.core.cache import ResultCache, cache_key
from enki_research.core.db import Database
from enki_research.models import SearchRequest, SearchResponse, SearchResult


@pytest.fixture
def db():
    database = Database(":memory:")
    yield database
    database.close()


def test_cache_hit_and_expiration(db):
    cache = ResultCache(db)
    req = SearchRequest(query="test query", category="academic", depth="standard")
    key = cache_key(req)

    assert cache.get(key) is None

    res = SearchResponse(
        request_id="req1",
        query=req.query,
        category=req.category,
        results=[SearchResult(title="A", url="https://a.org", snippet="snippet")],
        providers_used=[],
        paid_calls=0,
        cache_hit=False,
    )

    # Save with 1 second TTL
    cache.put(key, res, ttl=1)
    cached = cache.get(key)
    assert cached is not None
    assert cached.results[0].title == "A"

    # Wait for expiration
    time.sleep(1.2)
    assert cache.get(key) is None
