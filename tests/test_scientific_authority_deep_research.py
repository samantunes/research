"""Tests for Scientific & Engineering Deep Research Refactoring:
1. Low-authority domain blocklist & URL filter (forums, blogs, AI skills)
2. Source tier scoring / re-ranking boosting high-authority domains
3. Internal requirement traceability IDs extraction & prompt injection
4. LLM output token limits & guaranteed complete reference rendering
5. Multi-retriever academic + web hybrid configuration
"""

import asyncio
from unittest.mock import AsyncMock, patch

from gpt_researcher.actions.markdown_processing import ensure_complete_references
from gpt_researcher.actions.retriever import (
    DEFAULT_EXCLUDE_DOMAINS,
    HIGH_AUTHORITY_DOMAINS,
    filter_low_authority_urls,
    get_source_authority_score,
    is_low_authority_url,
    rerank_sources_by_authority,
)
from gpt_researcher.config.config import Config
from gpt_researcher.config.variables.default import DEFAULT_CONFIG
from gpt_researcher.prompts import (
    ATOMIC_QUERIES_RULE,
    EPISTEMIC_HIERARCHY_RULE,
    TRACEABILITY_CONSTRAINT_RULE,
    PromptFamily,
    extract_requirement_ids,
)


def test_forum_blog_and_ai_skills_filtered_out():
    """Verify forum threads, SEO blogs, AI agent prompt repos and coursehero/scribd are stripped."""
    noise_urls = [
        "https://discourse.astropy.org/t/thread-on-hypothesis-testing/1234",
        "https://forum.discourse.group/topic/456",
        "https://www.reddit.com/r/astropy/comments/abc/unit_tests",
        "https://reddit.com/r/scientific_computing",
        "https://gitnux.com/astropy-usage-statistics-2024",
        "https://devgex.com/top-10-python-libraries",
        "https://skillsdirectory.com/agent/prompt-123",
        "https://skills-directory.com/curated-prompts",
        "https://github.com/prompts/library/blob/main/SKILL.md",
        "https://github.com/agentic/tools/skills/v&v/skill.md",
        "https://quora.com/What-is-astropy",
        "https://medium.com/@randomuser/astropy-opinion",
        "https://coursehero.com/file/12345/physics-assignment",
        "https://scribd.com/document/98765/engineering-notes",
    ]

    for url in noise_urls:
        assert is_low_authority_url(url), f"Expected {url} to be detected as low-authority noise"

    # Verify high-authority sources are NOT filtered
    high_authority_urls = [
        "https://arxiv.org/abs/2104.12345",
        "https://dl.acm.org/doi/10.1145/123456",
        "https://ieeexplore.ieee.org/document/9876543",
        "https://ntrs.nasa.gov/citations/20220012345",
        "https://standards.nasa.gov/standard/nasa/nasa-std-871913",
        "https://asme.org/codes-standards/find-codes-standards/v-v-10",
        "https://osti.gov/biblio/1234567",
        "https://par.nsf.gov/servlets/purl/10123456",
        "https://joss.theoj.org/papers/10.21105/joss.04567",
        "https://springer.com/chapter/10.1007/978-3-030-12345",
        "https://wiley.com/doi/10.1002/spe.1234",
        "https://astropy.readthedocs.io/en/stable/coordinates/index.html",
        "https://github.com/astropy/astropy/pull/12345",
    ]

    for url in high_authority_urls:
        assert not is_low_authority_url(url), f"Expected {url} to be accepted as high-authority"

    # Test filtering a mixed list of dicts (search results)
    search_results = [
        {"href": "https://discourse.astropy.org/t/123", "body": "forum speculation"},
        {"href": "https://arxiv.org/abs/2104.12345", "body": "peer reviewed paper"},
        {"href": "https://gitnux.com/blog", "body": "seo post"},
        {"href": "https://standards.nasa.gov/nasa-std-871913", "body": "NASA software safety standard"},
        {"href": "https://skillsdirectory.com/agent", "body": "agent directory"},
    ]

    filtered = filter_low_authority_urls(search_results)
    assert len(filtered) == 2
    assert filtered[0]["href"] == "https://arxiv.org/abs/2104.12345"
    assert filtered[1]["href"] == "https://standards.nasa.gov/nasa-std-871913"


def test_source_tier_scoring_and_reranking():
    """Verify high-authority scientific/engineering domains are boosted to top."""
    sources = [
        "https://random-blog.com/python-testing",
        "https://arxiv.org/abs/2301.99999",
        "https://general-tech.org/notes",
        "https://ieeexplore.ieee.org/document/12345",
        "https://astropy.readthedocs.io/en/latest",
    ]

    ranked = rerank_sources_by_authority(sources)
    # The top sources must be from HIGH_AUTHORITY_DOMAINS
    top_domains = [s.split("/")[2] for s in ranked[:3]]
    assert "arxiv.org" in top_domains
    assert "ieeexplore.ieee.org" in top_domains
    assert "astropy.readthedocs.io" in top_domains

    assert get_source_authority_score("https://arxiv.org/abs/1234") == 100
    assert get_source_authority_score("https://standards.nasa.gov/std") == 100
    assert get_source_authority_score("https://stanford.edu/paper.pdf") == 50
    assert get_source_authority_score("https://random-tech.com/post") == 10
    assert get_source_authority_score("https://reddit.com/r/all") == 0


def test_requirement_id_extraction_and_prompt_injection():
    """Verify internal project requirement IDs (T5-BL7, T5-4.3, T5-6.4) are preserved."""
    query = (
        "Generate a formal V&V report for scientific coordinate transformations satisfying "
        "requirements T5-BL7 (Equatorial baseline), T5-4.3 (Cartesian error bounds), "
        "and T5-6.4 (Precision verification protocols)."
    )

    extracted = extract_requirement_ids(query)
    assert extracted == ["T5-BL7", "T5-4.3", "T5-6.4"]

    # Verify search query generation prompt includes constraint, requirement IDs, and atomic queries rule
    search_prompt = PromptFamily.generate_search_queries_prompt(
        question=query, parent_query="", report_type="research_report", max_iterations=3
    )
    assert "TRACEABILITY CONSTRAINT" in search_prompt
    assert "ATOMIC QUERIES RULE" in search_prompt
    assert "Never combine more than 2 technical concepts" in search_prompt
    assert "T5-BL7" in search_prompt
    assert "T5-4.3" in search_prompt
    assert "T5-6.4" in search_prompt

    # Verify writer report prompt includes Epistemic Hierarchy and Traceability Constraint
    report_prompt = PromptFamily.generate_report_prompt(
        question=query,
        context="Academic papers on coordinate transforms",
        report_source="web",
        report_format="apa",
        total_words=1500,
    )
    assert EPISTEMIC_HIERARCHY_RULE in report_prompt
    assert TRACEABILITY_CONSTRAINT_RULE in report_prompt
    assert "T5-BL7" in report_prompt
    assert "T5-4.3" in report_prompt
    assert "T5-6.4" in report_prompt

    # Verify Deep Research synthesis prompt includes both rules
    deep_prompt = PromptFamily.generate_deep_research_prompt(
        question=query,
        context="Hierarchical academic evidence from IEEE and NASA",
        report_source="web",
        report_format="apa",
        total_words=2500,
    )
    assert EPISTEMIC_HIERARCHY_RULE in deep_prompt
    assert TRACEABILITY_CONSTRAINT_RULE in deep_prompt
    assert "T5-BL7" in deep_prompt


def test_llm_configuration_token_limits():
    """Verify token limits are configured to at least 8192 / 16384."""
    cfg = Config()

    assert cfg.smart_token_limit >= 16384
    assert cfg.fast_token_limit >= 8192
    assert cfg.strategic_token_limit >= 8192
    assert DEFAULT_CONFIG["SMART_TOKEN_LIMIT"] >= 16384
    assert DEFAULT_CONFIG["FAST_TOKEN_LIMIT"] >= 8192

    # Check multi-retriever default includes academic retriever
    assert "arxiv" in cfg.retrievers or "arxiv" in cfg.retriever


def test_guaranteed_complete_reference_rendering():
    """Verify that truncation mid-sentence is sealed and References are programmatically appended."""
    truncated_report = (
        "# Formal Verification Report\n\n"
        "## 1. Requirement T5-BL7 Verification\n"
        "The coordinate transformation precision was evaluated against NASA standards. "
        "As established by IEEE 754 precision analysis, the maximum observed residual was "
        "bounded by 1e-12 radians across all coordinate systems. Furthermore, under high-velocity"
    )  # Truncated mid-sentence without references

    visited_urls = {
        "https://discourse.astropy.org/t/thread",  # noise -> must be filtered
        "https://gitnux.com/stats",                 # noise -> must be filtered
        "https://arxiv.org/abs/2104.12345",         # high authority -> must appear first
        "https://standards.nasa.gov/nasa-std-871913", # high authority -> must appear first
        "https://github.com/astropy/astropy",       # high authority
    }

    result = ensure_complete_references(
        truncated_report,
        visited_urls=visited_urls,
    )

    # Must contain ## References header
    assert "## References" in result
    # Must have cleanly terminated the truncated sentence
    assert "..." in result or "under high-velocity" in result
    # Noise URLs must NOT be in references
    assert "discourse.astropy.org" not in result
    assert "gitnux.com" not in result
    # High-authority references must be present
    assert "https://arxiv.org/abs/2104.12345" in result
    assert "https://standards.nasa.gov/nasa-std-871913" in result
    assert "https://github.com/astropy/astropy" in result


def test_deep_research_subquery_generation_rules():
    """Verify deep research sub-query generation prompt enforces 50% academic targeting."""
    from gpt_researcher.skills.deep_research import DeepResearchSkill
    from types import SimpleNamespace

    mock_cfg = SimpleNamespace(
        strategic_llm_provider="openai",
        strategic_llm_model="gpt-5.4",
        reasoning_effort="medium",
        llm_kwargs={},
        deep_research_breadth=4,
        deep_research_depth=2,
        deep_research_concurrency=2,
    )
    mock_researcher = SimpleNamespace(
        cfg=mock_cfg,
        websocket=None,
        tone=None,
        headers={},
        visited_urls=set(),
    )

    skill = DeepResearchSkill(mock_researcher)

    # Intercept create_chat_completion to inspect prompt
    captured_messages = []

    async def mock_chat(messages, **kwargs):
        captured_messages.extend(messages)
        return '[{"query": "Method of Manufactured Solutions ASME", "researchGoal": "verify mathematical bounds"}]'

    with patch("gpt_researcher.skills.deep_research.create_chat_completion", side_effect=mock_chat):
        asyncio.run(skill.generate_search_queries("Verify requirement T5-4.3 with astropy", num_queries=4))

    assert len(captured_messages) > 0
    prompt_text = captured_messages[1]["content"]
    assert "AT LEAST 50%" in prompt_text
    assert "ASME" in prompt_text
    assert "NASA" in prompt_text
    assert "Method of Manufactured Solutions" in prompt_text
    assert "AST" in prompt_text
    assert "ATOMIC QUERIES RULE" in prompt_text
    assert "Never combine more than 2 technical concepts" in prompt_text
    assert "TRACEABILITY CONSTRAINT" in prompt_text
    assert "T5-4.3" in prompt_text
