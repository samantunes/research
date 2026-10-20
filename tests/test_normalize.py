import pytest
from enki_research.core.normalize import canonical_url, fuse
from enki_research.models import SearchResult


def test_canonical_url_tracking_and_www():
    u1 = "https://www.example.com/path/?utm_source=twitter&foo=bar&gclid=123"
    u2 = "http://example.com/path?foo=bar"
    assert canonical_url(u1) == canonical_url(u2)


def test_canonical_url_arxiv():
    u1 = "https://arxiv.org/abs/2301.12345v2"
    u2 = "http://arxiv.org/pdf/2301.12345"
    assert canonical_url(u1) == canonical_url(u2) == "arxiv:2301.12345"


def test_canonical_url_doi():
    u1 = "https://doi.org/10.1000/182"
    u2 = "http://dx.doi.org/10.1000/182/"
    assert canonical_url(u1) == canonical_url(u2) == "doi:10.1000/182"


def test_fuse_rrf_and_dedup():
    r1 = SearchResult(title="Doc 1", url="https://example.com/a", snippet="Short")
    r2 = SearchResult(title="Doc 1 full", url="https://www.example.com/a?utm_campaign=xyz", snippet="Longer snippet text here")
    r3 = SearchResult(title="Doc 2", url="https://example.com/b", snippet="Another doc")

    lists = {
        "provA": [r1, r3],
        "provB": [r2],
    }
    fused = fuse(lists, max_results=10)
    assert len(fused) == 2
    top = fused[0]
    assert top.canonical_url == canonical_url("https://example.com/a")
    assert set(top.providers) == {"provA", "provB"}
    assert top.snippet == "Longer snippet text here"
    assert top.score > 0
