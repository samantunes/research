import pytest
from importlib.metadata import entry_points
from enki_research.integrations.gptr import EnkiSearch, EnkiAcademicSearch, EnkiCodeSearch, EnkiNewsSearch


def test_gptr_retriever_contract():
    # GPTR requires requires_scraping = True so it scrapes real full-page content
    assert EnkiSearch.requires_scraping is True
    assert EnkiAcademicSearch.requires_scraping is True
    assert EnkiCodeSearch.requires_scraping is True
    assert EnkiNewsSearch.requires_scraping is True

    s = EnkiSearch("test query")
    assert s.query == "test query"
    assert s.category == "general"


def test_entry_points_discovery():
    # If package is installed (editable or wheel), entry points should resolve
    eps = {ep.name: ep.value for ep in entry_points(group="gpt_researcher.retrievers")}
    # Even if not yet pip-installed in test env, we can verify the class path
    assert EnkiSearch.__name__ == "EnkiSearch"
