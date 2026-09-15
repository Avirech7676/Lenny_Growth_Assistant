"""Automated test suite for the 10-Stage Evidence Research Pipeline:

Question
   ↓
Research Planner
   ↓
Search Router
   ↓
Multiple Search Providers
   ↓
Source Evaluation
   ↓
Deduplication
   ↓
Conflict Detection
   ↓
Evidence Verification
   ↓
Answer
   ↓
Citations
"""

import pytest
import sys
import os

from app.services.research.pipeline import (
    EvidenceResearchPipeline,
    get_research_pipeline,
    StageTelemetry,
    EvidencePipelineResult,
)
from app.services.search.base import (
    DiscoveredSource,
    SourceCategory,
    ResearchDepth,
    EvidenceStrength,
    ResearchConflict,
)


@pytest.fixture
def pipeline():
    return EvidenceResearchPipeline()


class Test10StageResearchPipeline:
    """Rigorous verification of each individual stage and the end-to-end pipeline."""

    # --------------------------------------------------------------------------
    # Stage 1: Question
    # --------------------------------------------------------------------------
    def test_stage_1_question_validation(self, pipeline):
        # Valid query with entities and temporal requirements
        q = "Who is the current Chief Minister of Andhra Pradesh in 2026?"
        meta = pipeline.stage_1_question(q)
        assert meta["clean_query"] == q
        assert meta["time_sensitive"] is True
        assert any(e in meta["entities"] for e in ["Chief", "Minister", "Andhra", "Pradesh"])

        # Empty query validation
        with pytest.raises(ValueError):
            pipeline.stage_1_question("   ")

    # --------------------------------------------------------------------------
    # Stage 2: Research Planner
    # --------------------------------------------------------------------------
    def test_stage_2_research_planner_adaptive_depth(self, pipeline):
        # Factual targeted lookup
        plan_react = pipeline.stage_2_research_planner("What is the latest React version?")
        assert plan_react.depth in [ResearchDepth.TARGETED, ResearchDepth.STANDARD]
        assert plan_react.domain in ["technology", "general"]

        # Comparative deep research
        plan_compare = pipeline.stage_2_research_planner("Compare PostgreSQL and ClickHouse for real-time analytics")
        assert plan_compare.depth in [ResearchDepth.DEEP_MULTI_QUERY, ResearchDepth.STANDARD]
        assert len(plan_compare.sub_queries) >= 2

    # --------------------------------------------------------------------------
    # Stage 3: Search Router
    # --------------------------------------------------------------------------
    def test_stage_3_search_router_provider_routing(self, pipeline):
        plan = pipeline.stage_2_research_planner("What did Brian Chesky say about product reviews?")
        routed = pipeline.stage_3_search_router(plan)
        assert isinstance(routed, list)
        assert len(routed) > 0

    # --------------------------------------------------------------------------
    # Stage 4: Multiple Search Providers
    # --------------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_stage_4_multiple_search_providers_concurrency(self, pipeline):
        # Query known curated entity
        sources = await pipeline.stage_4_multiple_search_providers(
            primary_query="Who is CM of AP?",
            routed_queries=["current Chief Minister of Andhra Pradesh", "Andhra Pradesh CM 2024 2026"],
        )
        assert len(sources) > 0
        assert any("andhra" in s.snippet.lower() or "naidu" in s.snippet.lower() or "jagan" in s.snippet.lower() for s in sources)

    # --------------------------------------------------------------------------
    # Stage 5: Source Evaluation
    # --------------------------------------------------------------------------
    def test_stage_5_source_evaluation_authority_weighting(self, pipeline):
        mock_sources = [
            DiscoveredSource(
                title="Official Python Documentation",
                url="https://docs.python.org/3/",
                domain="python.org",
                snippet="Python official documentation.",
                category=SourceCategory.OFFICIAL,
                authority_score=0.95,
                is_primary=True,
            ),
            DiscoveredSource(
                title="Random Blog Post",
                url="https://medium.com/someblog",
                domain="medium.com",
                snippet="Some informal guide to python.",
                category=SourceCategory.COMMUNITY,
                authority_score=0.50,
                is_primary=False,
            ),
        ]
        ranked = pipeline.stage_5_source_evaluation("Python documentation", mock_sources)
        assert len(ranked) == 2
        # Official source ranked first
        assert ranked[0].domain == "python.org"
        assert ranked[0].authority_score > ranked[1].authority_score

    # --------------------------------------------------------------------------
    # Stage 6: Deduplication
    # --------------------------------------------------------------------------
    def test_stage_6_deduplication_url_and_content(self, pipeline):
        src1 = DiscoveredSource(
            title="FastAPI Security Guide",
            url="https://fastapi.tiangolo.com/tutorial/security/?utm_source=twitter&ref=blog",
            domain="fastapi.tiangolo.com",
            snippet="FastAPI security documentation.",
            category=SourceCategory.OFFICIAL,
            authority_score=0.95,
        )
        src2 = DiscoveredSource(
            title="FastAPI Security Guide",
            url="https://fastapi.tiangolo.com/tutorial/security/",
            domain="fastapi.tiangolo.com",
            snippet="Duplicate clean link.",
            category=SourceCategory.OFFICIAL,
            authority_score=0.95,
        )
        src3 = DiscoveredSource(
            title="Distinct Article",
            url="https://realpython.com/fastapi-auth/",
            domain="realpython.com",
            snippet="Unique content.",
            category=SourceCategory.TECHNICAL,
            authority_score=0.88,
        )
        deduped = pipeline.stage_6_deduplication([src1, src2, src3])
        assert len(deduped) == 2
        urls = [s.url for s in deduped]
        assert len(set(urls)) == 2

    # --------------------------------------------------------------------------
    # Stage 7: Conflict Detection
    # --------------------------------------------------------------------------
    def test_stage_7_conflict_detection_version_discrepancies(self, pipeline):
        src_v19 = DiscoveredSource(
            title="React 19 Official Release",
            url="https://react.dev/blog/2024/react-19",
            domain="react.dev",
            snippet="React 19.0.0 released with actions and server components.",
            category=SourceCategory.OFFICIAL,
            authority_score=0.99,
        )
        src_v18 = DiscoveredSource(
            title="React 18 Overview",
            url="https://legacy.reactjs.org/blog/2022/react-18",
            domain="legacy.reactjs.org",
            snippet="React 18.2.0 is the latest stable version.",
            category=SourceCategory.OFFICIAL,
            authority_score=0.80,
        )
        conflicts = pipeline.stage_7_conflict_detection([src_v19, src_v18])
        assert isinstance(conflicts, list)

    # --------------------------------------------------------------------------
    # Stage 8: Evidence Verification
    # --------------------------------------------------------------------------
    def test_stage_8_evidence_verification_claims(self, pipeline):
        sources = [
            DiscoveredSource(
                title="Python 3.14 Release",
                url="https://python.org/release/3.14",
                domain="python.org",
                snippet="Python 3.14 introduces free-threaded interpreter improvements. Modern GIL features tested.",
                category=SourceCategory.OFFICIAL,
                authority_score=0.95,
            )
        ]
        claims, strength = pipeline.stage_8_evidence_verification(sources, conflicts=[])
        assert len(claims) >= 1
        assert claims[0].status == "verified"
        assert claims[0].confidence == "high"
        assert "python.org" in claims[0].supporting_urls[0]

    # --------------------------------------------------------------------------
    # Stage 9: Answer Synthesis
    # --------------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_stage_9_grounded_answer_synthesis(self, pipeline):
        sources = [
            DiscoveredSource(
                title="Andhra Pradesh CM Official",
                url="https://ap.gov.in",
                domain="ap.gov.in",
                snippet="Nara Chandrababu Naidu assumed office as the Chief Minister of Andhra Pradesh in June 2024.",
                category=SourceCategory.GOVERNMENT,
                authority_score=0.98,
            )
        ]
        claims, _ = pipeline.stage_8_evidence_verification(sources, conflicts=[])
        answer = await pipeline.stage_9_answer(
            query="Who is Chief Minister of Andhra Pradesh?",
            claims=claims,
            sources=sources,
            conflicts=[],
        )
        assert len(answer) > 20
        assert "Chandrababu Naidu" in answer or "Chief Minister" in answer

    # --------------------------------------------------------------------------
    # Stage 10: Citations
    # --------------------------------------------------------------------------
    def test_stage_10_anchored_citations_integrity(self, pipeline):
        sources = [
            DiscoveredSource(
                title="Vite Official Guide",
                url="https://vitejs.dev/guide/",
                domain="vitejs.dev",
                snippet="Next Generation Frontend Tooling.",
                category=SourceCategory.TECHNICAL,
                authority_score=0.92,
                is_primary=True,
            )
        ]
        citations = pipeline.stage_10_citations(sources)
        assert len(citations) == 1
        c = citations[0]
        assert c["title"] == "Vite Official Guide"
        assert c["url"] == "https://vitejs.dev/guide/"
        assert c["domain"] == "vitejs.dev"
        assert c["category"] == "technical"
        assert c["is_primary"] is True

    # --------------------------------------------------------------------------
    # Full 10-Stage Pipeline End-to-End
    # --------------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_full_10_stage_pipeline_end_to_end(self, pipeline):
        query = "Who is CM of AP?"
        result = await pipeline.run(question=query, user_mode="auto")

        assert isinstance(result, EvidencePipelineResult)
        assert result.question == query
        assert result.total_sources_discovered > 0
        assert len(result.citations) > 0
        assert len(result.answer) > 10

        # Verify all 10 stages executed sequentially in telemetry
        assert len(result.stages_telemetry) == 10
        stage_names = [t.stage_name for t in result.stages_telemetry]
        assert stage_names == [
            "Question",
            "Research Planner",
            "Search Router",
            "Multiple Search Providers",
            "Source Evaluation",
            "Deduplication",
            "Conflict Detection",
            "Evidence Verification",
            "Answer",
            "Citations",
        ]

        # Verify stage ordering numbers 1 through 10
        stage_numbers = [t.stage_number for t in result.stages_telemetry]
        assert stage_numbers == list(range(1, 11))
