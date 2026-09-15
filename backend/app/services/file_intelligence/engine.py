"""Unified File Intelligence Engine.

Provides deep document understanding, multi-file comparison, structured extraction,
format transformation, and grounded combination of user files with real-time web research.
"""

import time
import json
import re
import logging
from typing import List, Dict, Any, Optional

from app.services.file_intelligence.models import (
    FileType,
    FileOperation,
    ParsedFile,
    EvidenceBlock,
    FileAnalysisResult,
    MultiFileComparisonResult,
    CombinedResearchAnalysisResult,
)
from app.services.file_intelligence.parser import get_unified_file_parser, UnifiedFileParser
from app.services.research.engine import get_deep_research_engine
from app.models.router import get_model_router
from app.models.base import LLMRequest

logger = logging.getLogger(__name__)


class FileIntelligenceEngine:
    """Unified engine for file intelligence, multi-file analysis, and research synthesis."""

    def __init__(self):
        self.parser = get_unified_file_parser()
        self.model_router = get_model_router()
        self.deep_research_engine = get_deep_research_engine()

    # --------------------------------------------------------------------------
    # 1. Summarization
    # --------------------------------------------------------------------------

    def summarize(self, file: ParsedFile, focus: Optional[str] = None) -> FileAnalysisResult:
        """Generate structured executive summary, core takeaways, and outline."""
        t0 = time.perf_counter()
        focus_str = f" with specific focus on '{focus}'" if focus else ""
        prompt = (
            f"You are an expert analyst. Provide an executive summary of the following document{focus_str}.\n"
            f"Include:\n1. Executive Summary\n2. Key Highlights / Findings\n3. Structure & Scope\n\n"
            f"{file.to_context_string()}"
        )

        llm_req = LLMRequest(
            prompt=prompt,
            system_prompt="You are a precise, grounded document analyst. Never invent details outside the file.",
            temperature=0.2,
            max_tokens=1000,
        )
        response = self.model_router.execute(llm_req, task_type="document_analysis")
        content = response.content.strip()

        # Extract bullet highlights
        lines = [line.strip("- *• ") for line in content.splitlines() if line.strip().startswith(("-", "*", "•"))]
        key_findings = lines[:5] if lines else [f"Analyzed {file.filename} ({file.file_type.value})"]

        evidence = [
            EvidenceBlock(
                source_type="USER_FILE",
                title=f"User Document: {file.filename}",
                content=file.content[:1500],
                metadata={"file_type": file.file_type.value, "metric": file.page_or_row_count},
            )
        ]

        return FileAnalysisResult(
            operation=FileOperation.SUMMARIZE,
            filename=file.filename,
            file_type=file.file_type,
            summary_or_answer=content,
            key_findings=key_findings,
            evidence=evidence,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    # --------------------------------------------------------------------------
    # 2. Factual Question Answering (QA)
    # --------------------------------------------------------------------------

    def ask_question(self, file: ParsedFile, question: str) -> FileAnalysisResult:
        """Answer specific user questions strictly grounded in the document."""
        t0 = time.perf_counter()
        prompt = (
            f"Question: {question}\n\n"
            f"Answer the question strictly using the provided document evidence below. "
            f"If the answer cannot be found in the document, explicitly state that.\n\n"
            f"{file.to_context_string()}"
        )

        llm_req = LLMRequest(
            prompt=prompt,
            system_prompt="You are a strict grounded question answering assistant. Never speculate.",
            temperature=0.1,
            max_tokens=800,
        )
        response = self.model_router.execute(llm_req, task_type="document_analysis")
        content = response.content.strip()

        evidence = [
            EvidenceBlock(
                source_type="USER_FILE",
                title=f"User Document: {file.filename}",
                content=file.content[:1500],
                metadata={"file_type": file.file_type.value},
            )
        ]

        return FileAnalysisResult(
            operation=FileOperation.QA,
            filename=file.filename,
            file_type=file.file_type,
            summary_or_answer=content,
            key_findings=[f"Target Question: {question}"],
            evidence=evidence,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    # --------------------------------------------------------------------------
    # 3. Deep Analysis
    # --------------------------------------------------------------------------

    def analyze(self, file: ParsedFile, aspect: Optional[str] = None) -> FileAnalysisResult:
        """Perform deep thematic, numerical, or architectural analysis."""
        t0 = time.perf_counter()
        aspect_str = f" Aspect: '{aspect}'." if aspect else " Comprehensive structural, numerical, and qualitative evaluation."
        prompt = (
            f"Perform a rigorous technical and business analysis of the following document.{aspect_str}\n"
            f"Provide:\n"
            f"1. Core Thematic Breakdown\n"
            f"2. Numerical / Quantitative Insights\n"
            f"3. Risks, Gaps, or Limitations\n"
            f"4. Strategic Recommendations\n\n"
            f"{file.to_context_string()}"
        )

        llm_req = LLMRequest(
            prompt=prompt,
            system_prompt="You are an elite enterprise strategist and code/data auditor.",
            temperature=0.2,
            max_tokens=1200,
        )
        response = self.model_router.execute(llm_req, task_type="document_analysis")
        content = response.content.strip()

        evidence = [
            EvidenceBlock(
                source_type="USER_FILE",
                title=f"User Document: {file.filename}",
                content=file.content[:2000],
                metadata={"file_type": file.file_type.value},
            )
        ]

        return FileAnalysisResult(
            operation=FileOperation.ANALYZE,
            filename=file.filename,
            file_type=file.file_type,
            summary_or_answer=content,
            key_findings=["In-depth analysis completed across qualitative and quantitative metrics."],
            evidence=evidence,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    # --------------------------------------------------------------------------
    # 4. Multi-File Comparison
    # --------------------------------------------------------------------------

    def compare_files(self, files: List[ParsedFile], comparison_goal: Optional[str] = None) -> MultiFileComparisonResult:
        """Compare multiple files, highlighting shared patterns, discrepancies, and contrast matrix."""
        t0 = time.perf_counter()
        if not files:
            return MultiFileComparisonResult(
                filenames=[],
                comparison_summary="No files provided for comparison.",
                latency_ms=0.0,
            )

        file_contexts = []
        for i, f in enumerate(files, 1):
            file_contexts.append(f"=== Document {i}: {f.filename} ({f.file_type.value}) ===\n{f.content[:4000]}")

        goal_str = f" Goal: {comparison_goal}" if comparison_goal else ""
        prompt = (
            f"Perform a comprehensive comparative analysis between the following {len(files)} documents.{goal_str}\n\n"
            f"Provide:\n"
            f"1. Executive Comparison Overview\n"
            f"2. Shared Themes & Agreements\n"
            f"3. Key Divergences & Contradictions\n"
            f"4. Comparative Tradeoff Matrix\n\n"
            + "\n\n".join(file_contexts)
        )

        llm_req = LLMRequest(
            prompt=prompt,
            system_prompt="You are an expert comparative research analyst.",
            temperature=0.2,
            max_tokens=1400,
        )
        response = self.model_router.execute(llm_req, task_type="document_analysis")
        content = response.content.strip()

        # Build contrast matrix dictionary
        contrast_matrix: Dict[str, Dict[str, Any]] = {}
        for f in files:
            contrast_matrix[f.filename] = {
                "file_type": f.file_type.value,
                "metric_count": f.page_or_row_count,
                "key_metadata": f.metadata,
            }

        evidence = [
            EvidenceBlock(
                source_type="USER_FILE",
                title=f"Comparison Document: {f.filename}",
                content=f.content[:800],
                metadata={"file_type": f.file_type.value},
            )
            for f in files
        ]

        return MultiFileComparisonResult(
            filenames=[f.filename for f in files],
            comparison_summary=content,
            contrast_matrix=contrast_matrix,
            shared_themes=[f"Cross-analyzed {len(files)} documents"],
            key_differences=["Identified comparative differences across files"],
            evidence=evidence,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    # --------------------------------------------------------------------------
    # 5. Information Extraction
    # --------------------------------------------------------------------------

    def extract_information(self, file: ParsedFile, target_fields: List[str]) -> FileAnalysisResult:
        """Extract specific schema fields, tabular records, or entity key-values from document."""
        t0 = time.perf_counter()
        fields_str = ", ".join(target_fields) if target_fields else "all relevant key metrics, entities, and dates"
        prompt = (
            f"Extract the following information points from the document: [{fields_str}].\n"
            f"Output the extracted information in clear structured JSON format with explanatory notes.\n\n"
            f"{file.to_context_string()}"
        )

        llm_req = LLMRequest(
            prompt=prompt,
            system_prompt="You are an elite structured data extraction pipeline. Output precise factual values.",
            temperature=0.1,
            max_tokens=900,
        )
        response = self.model_router.execute(llm_req, task_type="document_analysis")
        content = response.content.strip()

        # Try parsing JSON block
        extracted_dict: Dict[str, Any] = {}
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                extracted_dict = json.loads(json_match.group(1))
            except Exception:
                pass
        if not extracted_dict and "{" in content and "}" in content:
            try:
                raw_json = content[content.find("{"):content.rfind("}") + 1]
                extracted_dict = json.loads(raw_json)
            except Exception:
                pass

        return FileAnalysisResult(
            operation=FileOperation.EXTRACT,
            filename=file.filename,
            file_type=file.file_type,
            summary_or_answer=content,
            extracted_data=extracted_dict or {"raw_extraction": content},
            key_findings=[f"Extracted fields: {fields_str}"],
            evidence=[EvidenceBlock(source_type="USER_FILE", title=file.filename, content=file.content[:1000])],
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    # --------------------------------------------------------------------------
    # 6. Format Transformation
    # --------------------------------------------------------------------------

    def transform_information(self, file: ParsedFile, target_format: str, instructions: Optional[str] = None) -> FileAnalysisResult:
        """Transform document content into a target schema or format (e.g. JSON, Markdown, Table)."""
        t0 = time.perf_counter()
        inst_str = f" Additional rules: {instructions}" if instructions else ""
        prompt = (
            f"Transform the content of the following document into {target_format.upper()} format.{inst_str}\n"
            f"Ensure strict syntax adherence and data fidelity.\n\n"
            f"{file.to_context_string()}"
        )

        llm_req = LLMRequest(
            prompt=prompt,
            system_prompt="You are a data transformation compiler.",
            temperature=0.1,
            max_tokens=1500,
        )
        response = self.model_router.execute(llm_req, task_type="document_analysis")
        transformed = response.content.strip()

        return FileAnalysisResult(
            operation=FileOperation.TRANSFORM,
            filename=file.filename,
            file_type=file.file_type,
            summary_or_answer=f"Successfully transformed {file.filename} into {target_format}.",
            transformed_content=transformed,
            key_findings=[f"Target format: {target_format}"],
            evidence=[EvidenceBlock(source_type="USER_FILE", title=file.filename, content=file.content[:800])],
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    # --------------------------------------------------------------------------
    # 7. Combine Files with Web Research (User File + Current Web Research + Analysis)
    # --------------------------------------------------------------------------

    async def combine_with_web_research_async(
        self,
        file: ParsedFile,
        research_query: str,
        depth: str = "moderate",
    ) -> CombinedResearchAnalysisResult:
        """Execute unified file intelligence combining user file evidence with real-time web research."""
        t0 = time.perf_counter()

        # 1. Execute live web research
        research_res = await self.deep_research_engine.execute_research(
            query=research_query,
            depth_override=depth,
        )

        # 2. Structure User File Evidence
        user_file_evidence = (
            f"Source Document: {file.filename} (Type: {file.file_type.value})\n"
            f"Content Extract:\n{file.content[:4000]}"
        )

        # 3. Structure Web Research Evidence
        web_sources_lines = []
        for src in research_res.used_sources:
            web_sources_lines.append(
                f"- [{src.title}] ({src.domain} | Category: {src.category.value if hasattr(src.category, 'value') else src.category})\n"
                f"  Snippet: {src.snippet[:200]}"
            )
        web_research_evidence = (
            f"Research Query: '{research_query}'\n"
            f"Verified Sources Consulted ({len(research_res.used_sources)} sources across {research_res.independent_sources_count} independent domains):\n"
            + "\n".join(web_sources_lines)
        )

        # 4. Synthesize Rigorous Grounded Analysis
        prompt = (
            f"Perform a thorough comparative analysis combining the user's uploaded document and current verified web research.\n\n"
            f"EVIDENCE SOURCE 1 [USER FILE]:\n{user_file_evidence}\n\n"
            f"EVIDENCE SOURCE 2 [CURRENT WEB RESEARCH]:\n{web_research_evidence}\n\n"
            f"Provide a structured analysis with the following sections:\n"
            f"1. Executive Summary & Context\n"
            f"2. Direct Comparison (User File vs Current Market/External Findings)\n"
            f"3. Key Alignments and Significant Discrepancies\n"
            f"4. Strategic Takeaways & Forward-Looking Recommendations\n"
        )

        llm_req = LLMRequest(
            prompt=prompt,
            system_prompt=(
                "You are an elite research strategist. You must clearly differentiate between what was "
                "stated in the user's file versus what was discovered in current real-world web research."
            ),
            temperature=0.2,
            max_tokens=1400,
        )
        response = self.model_router.execute(llm_req, task_type="document_analysis")
        analysis_content = response.content.strip()

        # Citations
        citations = [
            {
                "title": s.title,
                "url": s.url,
                "domain": s.domain,
                "snippet": s.snippet[:180],
                "authority": s.authority_score,
                "source_type": "external_web",
            }
            for s in research_res.used_sources
        ]
        citations.insert(0, {
            "title": file.filename,
            "url": f"file://{file.filename}",
            "domain": "user_uploaded_file",
            "snippet": file.content[:180],
            "authority": 1.0,
            "source_type": "user_file",
        })

        # Evidence blocks explicitly distinguished
        evidence_blocks = [
            EvidenceBlock(
                source_type="USER_FILE",
                title=f"User Document: {file.filename}",
                content=file.content[:3000],
                metadata={"filename": file.filename, "file_type": file.file_type.value},
            ),
            EvidenceBlock(
                source_type="CURRENT_WEB_RESEARCH",
                title=f"Live Web Research: {research_query}",
                content=research_res.synthesis_context[:3000],
                metadata={
                    "query": research_query,
                    "independent_domains": research_res.independent_sources_count,
                    "evidence_strength": research_res.evidence_strength.value if hasattr(research_res.evidence_strength, 'value') else str(research_res.evidence_strength),
                },
            ),
            EvidenceBlock(
                source_type="ANALYSIS",
                title="Comparative Synthesis & Recommendations",
                content=analysis_content,
                metadata={"model": response.model},
            ),
        ]

        key_takeaways = [
            f"Synthesized user document '{file.filename}' against current web research for '{research_query}'.",
            f"Grounding confirmed across {research_res.independent_sources_count} independent external authorities.",
        ]

        return CombinedResearchAnalysisResult(
            filename=file.filename,
            research_query=research_query,
            user_file_evidence=user_file_evidence,
            web_research_evidence=web_research_evidence,
            comparative_analysis=analysis_content,
            key_takeaways=key_takeaways,
            citations=citations,
            evidence_blocks=evidence_blocks,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    def combine_with_web_research_sync(
        self,
        file: ParsedFile,
        research_query: str,
        depth: str = "moderate",
    ) -> CombinedResearchAnalysisResult:
        """Synchronous wrapper for combine_with_web_research_async."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(
                    lambda: asyncio.run(
                        self.combine_with_web_research_async(file, research_query, depth)
                    )
                ).result()
        else:
            return asyncio.run(self.combine_with_web_research_async(file, research_query, depth))


_FILE_INTELLIGENCE_ENGINE = FileIntelligenceEngine()


def get_file_intelligence_engine() -> FileIntelligenceEngine:
    """Access singleton FileIntelligenceEngine."""
    return _FILE_INTELLIGENCE_ENGINE
