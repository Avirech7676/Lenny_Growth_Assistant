"""Tests for Layer 5: Coding Agent & Repository Intelligence."""

import os
import pytest
from app.services.coding.agent import (
    RepositoryInspector,
    SyntaxValidator,
    CodePlanner,
    CodingAgent,
    get_coding_agent,
    _detect_language,
    MAX_FILE_READ_BYTES,
)


@pytest.fixture
def workspace_root():
    # Points to project root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_detect_language():
    assert _detect_language("app/main.py") == "python"
    assert _detect_language("src/App.jsx") in ["jsx", "javascript"]
    assert _detect_language("styles.css") == "css"
    assert _detect_language("data.json") == "json"
    assert _detect_language("README.md") == "markdown"
    assert _detect_language("unknown.xyz") == "text"


def test_repository_inspector_tree(workspace_root):
    inspector = RepositoryInspector(workspace_root)
    tree = inspector.directory_tree(".", depth=2)
    assert tree is not None
    assert tree.is_dir is True

    # Children should include backend and frontend
    child_names = [c.name for c in tree.children]
    assert "backend" in child_names or "frontend" in child_names

    # Check formatted tree string
    formatted = inspector.format_tree_for_llm(tree)
    assert "backend" in formatted or "frontend" in formatted


def test_repository_inspector_security_traversal(workspace_root):
    inspector = RepositoryInspector(workspace_root)
    # Attempt directory traversal attack
    content, err = inspector.read_file("../../secret.txt")
    assert content is None
    assert "traversal" in err.lower()

    content, err = inspector.read_file("c:\\Windows\\System32\\calc.exe")
    assert content is None
    assert "traversal" in err.lower()


def test_repository_inspector_read_valid_file(workspace_root):
    inspector = RepositoryInspector(workspace_root)
    content, err = inspector.read_file("backend/app/main.py")
    assert err is None
    assert content is not None
    assert "FastAPI" in content or "app" in content


def test_syntax_validator_python():
    validator = SyntaxValidator()

    # Valid Python code
    valid_py = "def add(a: int, b: int) -> int:\n    return a + b\n"
    res = validator.validate(valid_py, "calculator.py")
    assert res.valid is True
    assert len(res.errors) == 0
    assert res.language == "python"

    # Invalid Python code
    invalid_py = "def broken(:\n    return 42\n"
    res_bad = validator.validate(invalid_py, "broken.py")
    assert res_bad.valid is False
    assert len(res_bad.errors) > 0
    assert "SyntaxError" in res_bad.errors[0]


def test_syntax_validator_json():
    validator = SyntaxValidator()

    # Valid JSON
    valid_json = '{"name": "Assistant", "version": 2}'
    res = validator.validate(valid_json, "config.json")
    assert res.valid is True

    # Invalid JSON
    invalid_json = '{"name": "Assistant", "trailing_comma": true,}'
    res_bad = validator.validate(invalid_json, "config.json")
    assert res_bad.valid is False
    assert len(res_bad.errors) > 0


def test_code_planner():
    planner = CodePlanner()
    plan = planner.plan(
        goal="Implement async database connection pool with health check for FastAPI",
        repo_context="FastAPI backend with SQLAlchemy"
    )
    assert plan.goal is not None
    assert len(plan.steps) >= 3
    # Steps are descriptive strings
    assert any("implement" in s.lower() or "design" in s.lower() or "architecture" in s.lower() for s in plan.steps)

    # Check formatting
    formatted = plan.format_for_llm()
    assert "IMPLEMENTATION STEPS:" in formatted
    assert "1." in formatted


def test_coding_agent_context_building(workspace_root):
    agent = CodingAgent(workspace_root)
    ctx = agent.build_context_for_llm(
        goal="Fix orchestrator routing",
        target_files=["backend/app/main.py"]
    )
    assert "REPOSITORY STRUCTURE" in ctx
    assert "IMPLEMENTATION PLAN" in ctx
    assert "FILE: backend/app/main.py" in ctx
