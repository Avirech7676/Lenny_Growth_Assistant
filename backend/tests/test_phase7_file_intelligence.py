"""Phase 7 Test Suite: Unified File Intelligence System.

Tests all supported formats:
- PDF (.pdf)
- DOCX (.docx)
- XLSX (.xlsx)
- CSV (.csv)
- JSON (.json, .jsonl)
- TXT (.txt)
- Markdown (.md)
- Source code (.py, .ts, .sql)
- Images (.png, .jpg)

Tests all user operations:
- Summarize
- Ask questions (QA)
- Analyze
- Compare files
- Extract information
- Transform information
- Combine files with web research (USER FILE + CURRENT WEB RESEARCH + ANALYSIS)

Validates the exact required scenario:
"Analyze this PDF and compare it with current market information."
"""

import io
import json
import pytest
import asyncio
from typing import List

from app.services.file_intelligence import (
    FileType,
    FileOperation,
    ParsedFile,
    get_unified_file_parser,
    get_file_intelligence_engine,
    FileAnalysisResult,
    MultiFileComparisonResult,
    CombinedResearchAnalysisResult,
)


@pytest.fixture
def parser():
    return get_unified_file_parser()


@pytest.fixture
def engine():
    return get_file_intelligence_engine()


# ------------------------------------------------------------------------------
# 1. Multi-Format Parsing Tests
# ------------------------------------------------------------------------------

def test_parse_pdf(parser):
    """Verify PDF parsing, page count, and metadata extraction."""
    import pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    data = buf.getvalue()

    parsed = parser.parse_bytes("annual_report.pdf", data)
    assert parsed.file_type == FileType.PDF
    assert parsed.page_or_row_count >= 1
    assert parsed.is_success


def test_parse_docx(parser):
    """Verify DOCX parsing with headings and paragraphs."""
    import docx
    doc = docx.Document()
    doc.add_heading("Q3 Strategic Roadmap", level=1)
    doc.add_paragraph("Expansion into APAC cloud infrastructure scheduled for Q4.")
    buf = io.BytesIO()
    doc.save(buf)
    data = buf.getvalue()

    parsed = parser.parse_bytes("roadmap.docx", data)
    assert parsed.file_type == FileType.DOCX
    assert "Strategic Roadmap" in parsed.content
    assert "APAC" in parsed.content
    assert parsed.is_success


def test_parse_xlsx(parser):
    """Verify multi-sheet XLSX parsing and row counts."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Revenue"
    ws.append(["Region", "2025_ARR", "2026_Projected"])
    ws.append(["North America", "$45M", "$62M"])
    ws.append(["EMEA", "$28M", "$39M"])
    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()

    parsed = parser.parse_bytes("financials.xlsx", data)
    assert parsed.file_type == FileType.XLSX
    assert "North America" in parsed.content
    assert "$45M" in parsed.content
    assert parsed.page_or_row_count >= 3
    assert parsed.is_success


def test_parse_csv(parser):
    """Verify CSV tabular parsing."""
    csv_text = "id,name,role,department\n1,Alice,Lead Engineer,Platform\n2,Bob,Product Manager,Growth\n"
    parsed = parser.parse_bytes("team.csv", csv_text.encode("utf-8"))
    assert parsed.file_type == FileType.CSV
    assert "Alice" in parsed.content
    assert "Lead Engineer" in parsed.content
    assert parsed.page_or_row_count == 3


def test_parse_json(parser):
    """Verify JSON structure parsing and formatting."""
    json_data = {"system": "Lenny Growth", "version": "2.0", "status": "active", "models": ["gemini", "groq"]}
    parsed = parser.parse_bytes("config.json", json.dumps(json_data).encode("utf-8"))
    assert parsed.file_type == FileType.JSON
    assert "Lenny Growth" in parsed.content
    assert "active" in parsed.content


def test_parse_txt_and_markdown(parser):
    """Verify plain text and markdown parsing."""
    md_text = "# Project Antigravity\n\n- Feature 1: Multi-model router\n- Feature 2: Deep research"
    parsed = parser.parse_bytes("readme.md", md_text.encode("utf-8"))
    assert parsed.file_type == FileType.MARKDOWN
    assert "Project Antigravity" in parsed.content

    txt_text = "Plain log output:\n[2026-09-14] Cluster initialized."
    parsed_txt = parser.parse_bytes("server.txt", txt_text.encode("utf-8"))
    assert parsed_txt.file_type == FileType.TXT
    assert "Cluster initialized" in parsed_txt.content


def test_parse_source_code(parser):
    """Verify source code syntax wrap across Python, TypeScript, and SQL."""
    py_code = "def calculate_growth(mrr_start, mrr_end):\n    return (mrr_end - mrr_start) / mrr_start"
    parsed_py = parser.parse_bytes("metrics.py", py_code.encode("utf-8"))
    assert parsed_py.file_type == FileType.CODE
    assert "```python" in parsed_py.content

    sql_code = "SELECT user_id, COUNT(*) FROM events GROUP BY user_id HAVING COUNT(*) > 10;"
    parsed_sql = parser.parse_bytes("retention.sql", sql_code.encode("utf-8"))
    assert parsed_sql.file_type == FileType.CODE
    assert "```sql" in parsed_sql.content


def test_parse_image(parser):
    """Verify image metadata extraction via Pillow."""
    from PIL import Image
    img = Image.new("RGB", (640, 480), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    parsed = parser.parse_bytes("architecture_diagram.png", data)
    assert parsed.file_type == FileType.IMAGE
    assert "640 x 480 pixels" in parsed.content
    assert parsed.metadata["format"] == "PNG"
    assert parsed.metadata["width"] == 640
    assert parsed.metadata["height"] == 480


# ------------------------------------------------------------------------------
# 2. File Operations Tests
# ------------------------------------------------------------------------------

def test_operation_summarize(engine, parser):
    """Verify document summarization operation."""
    text = (
        "Q3 2026 Shareholder Memo:\n"
        "Revenue increased 35% year-over-year to $120M. Key growth driver was enterprise AI agents. "
        "Operating margin expanded by 450 basis points. Customer retention reached 94% with net churn at -2%. "
        "Management guides full-year revenue upwards to $490M."
    )
    doc = parser.parse_bytes("shareholder_memo.txt", text.encode("utf-8"))
    res = engine.summarize(doc)

    assert isinstance(res, FileAnalysisResult)
    assert res.operation == FileOperation.SUMMARIZE
    assert res.filename == "shareholder_memo.txt"
    assert len(res.summary_or_answer) > 20
    assert len(res.evidence) >= 1
    assert res.evidence[0].source_type == "USER_FILE"


def test_operation_ask_questions_qa(engine, parser):
    """Verify factual QA grounded strictly in document content."""
    text = (
        "Project Orion Architecture:\n"
        "The authentication layer uses Ed25519 asymmetric signatures with a 15-minute token TTL. "
        "The primary caching tier uses Redis Cluster with 6 shards. "
        "Cold storage is archived in AWS S3 Glacier with a 90-day lifecycle rule."
    )
    doc = parser.parse_bytes("architecture.txt", text.encode("utf-8"))
    res = engine.ask_question(doc, "What is the token TTL and signature algorithm?")

    assert isinstance(res, FileAnalysisResult)
    assert res.operation == FileOperation.QA
    assert "15" in res.summary_or_answer
    assert "Ed25519" in res.summary_or_answer or "ed25519" in res.summary_or_answer.lower()
    assert res.evidence[0].source_type == "USER_FILE"


def test_operation_analyze(engine, parser):
    """Verify deep document analysis operation."""
    text = (
        "SaaS Unit Economics Audit:\n"
        "Customer Acquisition Cost (CAC) is $4,200. Average Revenue Per Account (ARPA) is $600/month. "
        "Payback period is 7 months. Gross margin is 81%. Net Revenue Retention (NRR) is 128%."
    )
    doc = parser.parse_bytes("unit_economics.txt", text.encode("utf-8"))
    res = engine.analyze(doc, aspect="Capital efficiency and scaling risks")

    assert isinstance(res, FileAnalysisResult)
    assert res.operation == FileOperation.ANALYZE
    assert len(res.summary_or_answer) > 50


def test_operation_compare_files(engine, parser):
    """Verify multi-file comparison between two documents."""
    doc1 = parser.parse_bytes(
        "v1_policy.txt",
        b"Version 1: Free tier allows 100 requests per day. Maximum upload size is 5MB. No API access."
    )
    doc2 = parser.parse_bytes(
        "v2_policy.txt",
        b"Version 2: Free tier allows 1,000 requests per day. Maximum upload size is 25MB. API access included."
    )

    res = engine.compare_files([doc1, doc2], comparison_goal="Identify tier upgrade changes")

    assert isinstance(res, MultiFileComparisonResult)
    assert res.operation == FileOperation.COMPARE
    assert len(res.filenames) == 2
    assert "v1_policy.txt" in res.contrast_matrix
    assert "v2_policy.txt" in res.contrast_matrix
    assert len(res.evidence) == 2
    assert all(e.source_type == "USER_FILE" for e in res.evidence)


def test_operation_extract_information(engine, parser):
    """Verify structured information extraction."""
    text = (
        "Server Deployment Config:\n"
        "Hostname: api-prod-us-east-1.internal\n"
        "IP Address: 10.0.4.12\n"
        "Port: 8443\n"
        "Max Connections: 10000\n"
        "Environment: production\n"
    )
    doc = parser.parse_bytes("config.txt", text.encode("utf-8"))
    res = engine.extract_information(doc, target_fields=["Hostname", "Port", "Max Connections"])

    assert isinstance(res, FileAnalysisResult)
    assert res.operation == FileOperation.EXTRACT
    assert res.extracted_data is not None


def test_operation_transform_information(engine, parser):
    """Verify format transformation from CSV to JSON format."""
    csv_text = "product,sku,price,stock\nWidget A,W-100,19.99,150\nWidget B,W-200,34.50,85\n"
    doc = parser.parse_bytes("inventory.csv", csv_text.encode("utf-8"))
    res = engine.transform_information(doc, target_format="json", instructions="Output array of JSON objects")

    assert isinstance(res, FileAnalysisResult)
    assert res.operation == FileOperation.TRANSFORM
    assert res.transformed_content is not None
    assert "Widget A" in res.transformed_content


# ------------------------------------------------------------------------------
# 3. Exact Scenario: User File + Current Web Research + Analysis
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_combine_file_with_web_research_exact_scenario(engine, parser):
    """Verify exact prompt scenario:

    'Analyze this PDF and compare it with current market information.'
    The system must use:
    USER FILE + CURRENT WEB RESEARCH + ANALYSIS
    and clearly distinguish each evidence source.
    """
    # Create realistic user PDF document content
    pdf_text = (
        "Internal Product Strategy Memo (Dated 2023):\n"
        "Our flagship product relies on React 18 for frontend rendering and Python 3.10 with standard GIL for backend. "
        "We consider FastAPI a niche alternative and stick with Django. We expect React 19 to remain unreleased until 2027."
    )
    doc = parser.parse_bytes("product_strategy_memo.pdf", pdf_text.encode("utf-8"))

    # Execute combination with current 2026 market research
    res = await engine.combine_with_web_research_async(
        file=doc,
        research_query="What is the latest React version and current status",
        depth="moderate",
    )

    assert isinstance(res, CombinedResearchAnalysisResult)
    assert res.operation == FileOperation.COMBINE_WITH_WEB_RESEARCH
    assert res.filename == "product_strategy_memo.pdf"

    # Verify each of the three required evidence sources is explicitly populated:
    # 1. USER FILE
    assert len(res.user_file_evidence) > 0
    assert "product_strategy_memo.pdf" in res.user_file_evidence
    assert "React 18" in res.user_file_evidence

    # 2. CURRENT WEB RESEARCH
    assert len(res.web_research_evidence) > 0
    assert "react.dev" in res.web_research_evidence.lower() or "react" in res.web_research_evidence.lower()

    # 3. ANALYSIS
    assert len(res.comparative_analysis) > 0

    # Verify structured evidence blocks explicitly separate the three sources:
    source_types = [eb.source_type for eb in res.evidence_blocks]
    assert "USER_FILE" in source_types
    assert "CURRENT_WEB_RESEARCH" in source_types
    assert "ANALYSIS" in source_types

    # Verify formatted report output
    formatted_report = res.to_formatted_report()
    assert "[EVIDENCE SOURCE: USER FILE]" in formatted_report
    assert "[EVIDENCE SOURCE: CURRENT WEB RESEARCH]" in formatted_report
    assert "[ANALYSIS & SYNTHESIS]" in formatted_report


# ------------------------------------------------------------------------------
# 4. API Endpoints Tests
# ------------------------------------------------------------------------------

def test_api_file_intelligence_endpoint():
    """Verify HTTP POST /api/v1/files/intelligence executes operations correctly."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. Test Summarize
    file_bytes = b"Executive Brief: Antigravity v2.0 deployed across 4 regions with 99.99% uptime."
    res = client.post(
        "/api/v1/files/intelligence",
        files={"file": ("brief.txt", file_bytes, "text/plain")},
        data={"operation": "summarize"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["operation"] == "summarize"
    assert data["filename"] == "brief.txt"

    # 2. Test QA
    res_qa = client.post(
        "/api/v1/files/intelligence",
        files={"file": ("brief.txt", file_bytes, "text/plain")},
        data={"operation": "qa", "query": "What is the uptime and region count?"},
    )
    assert res_qa.status_code == 200
    assert "99.99" in res_qa.json()["summary_or_answer"]
