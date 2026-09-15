"""Automated Test Suite for Phase 4: First-Class Coding Agent & Multi-Language Execution Sandbox.

Validates:
1. Multi-Language Sandboxed Execution:
   - Python
   - JavaScript/TypeScript
   - Java
   - C++
   - SQL
   - FastAPI
   - React
2. Sandbox Security Isolation & Resource Limits:
   - Untrusted code injection blocked
   - AST & pattern security enforcement
   - Timeout enforcement
3. All 12 First-Class Coding Capabilities:
   - code generation
   - code explanation
   - debugging
   - refactoring
   - optimization
   - code review
   - test generation
   - architecture
   - repository analysis
   - dependency analysis
   - API implementation
   - database implementation
4. 9-Phase Repository Task Lifecycle:
   INSPECT → UNDERSTAND → PLAN → MODIFY → BUILD → TEST → FIX → RETEST → REVIEW
5. Epistemic Verification Truth:
   Never claim code works unless it was actually executed or tested.
"""

import pytest
import shutil

from app.coding.types import (
    CodingCapability,
    CodingAgentRequest,
    ExecutionLanguage,
    RepoTaskPhase,
    SandboxExecutionRequest,
)
from app.coding.sandbox import SandboxExecutionEngine
from app.coding.repo_engine import RepoTaskEngine
from app.coding.agent import CodingAgent, get_coding_agent


@pytest.fixture
def sandbox():
    return SandboxExecutionEngine()


@pytest.fixture
def repo_engine():
    return RepoTaskEngine()


@pytest.fixture
def agent():
    return CodingAgent()


# ==============================================================================
# 1. Multi-Language Sandboxed Execution Tests
# ==============================================================================

class TestSandboxMultiLanguageExecution:
    """Test safe, isolated sandboxed execution across all supported languages."""

    @pytest.mark.anyio
    async def test_python_sandbox_execution_success(self, sandbox):
        code = (
            "def fibonacci(n):\n"
            "    a, b = 0, 1\n"
            "    for _ in range(n):\n"
            "        a, b = b, a + b\n"
            "    return a\n\n"
            "print(f'FIB_10={fibonacci(10)}')"
        )
        res = await sandbox.execute_python(code)
        assert res.success is True
        assert res.verified is True
        assert res.exit_code == 0
        assert "FIB_10=55" in res.stdout
        assert res.security_violation is None

    @pytest.mark.anyio
    async def test_python_sandbox_ast_security_rejection(self, sandbox):
        # Disallow ctypes
        malicious_code_1 = "import ctypes\nprint('pwnd')"
        res_1 = await sandbox.execute_python(malicious_code_1)
        assert res_1.success is False
        assert "prohibited in the sandbox" in res_1.stderr

        # Disallow subprocess
        malicious_code_2 = "import subprocess\nsubprocess.run(['dir'])"
        res_2 = await sandbox.execute_python(malicious_code_2)
        assert res_2.success is False
        assert "prohibited in the sandbox" in res_2.stderr

    @pytest.mark.anyio
    async def test_python_sandbox_timeout_handling(self, sandbox):
        infinite_code = "import time\ntime.sleep(5)"
        res = await sandbox.execute_python(infinite_code, timeout_seconds=1.0)
        assert res.success is False
        assert res.exit_code == 124
        assert "timed out" in res.stderr.lower()

    @pytest.mark.anyio
    async def test_javascript_sandbox_execution_success(self, sandbox):
        if not shutil.which("node"):
            pytest.skip("Node.js binary not available on host")
        js_code = (
            "const nums = [1, 2, 3, 4, 5];\n"
            "const sum = nums.reduce((acc, x) => acc + x, 0);\n"
            "console.log(`SUM=${sum}`);"
        )
        res = await sandbox.execute_javascript(js_code)
        assert res.success is True
        assert res.exit_code == 0
        assert "SUM=15" in res.stdout

    @pytest.mark.anyio
    async def test_javascript_sandbox_security_rejection(self, sandbox):
        bad_js = "const cp = require('child_process'); cp.exec('dir');"
        res = await sandbox.execute_javascript(bad_js)
        assert res.success is False
        assert "Prohibited pattern" in res.stderr

    @pytest.mark.anyio
    async def test_java_sandbox_execution_success(self, sandbox):
        if not shutil.which("javac") or not shutil.which("java"):
            pytest.skip("Java JDK not installed on host")
        java_code = (
            "public class QuickSort {\n"
            "    public static void main(String[] args) {\n"
            "        System.out.println(\"JAVA_SANDBOX_OK\");\n"
            "    }\n"
            "}\n"
        )
        res = await sandbox.execute_java(java_code)
        assert res.success is True
        assert res.exit_code == 0
        assert "JAVA_SANDBOX_OK" in res.stdout

    @pytest.mark.anyio
    async def test_java_sandbox_security_rejection(self, sandbox):
        bad_java = (
            "public class Exploit {\n"
            "    public static void main(String[] args) {\n"
            "        Runtime.getRuntime().exec(\"calc.exe\");\n"
            "    }\n"
            "}\n"
        )
        res = await sandbox.execute_java(bad_java)
        assert res.success is False
        assert "Prohibited Java operation" in res.stderr

    @pytest.mark.anyio
    async def test_sql_in_memory_sandbox(self, sandbox):
        ddl = (
            "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, tier TEXT);\n"
            "INSERT INTO customers VALUES (1, 'Alice', 'enterprise'), (2, 'Bob', 'starter');\n"
        )
        query = "SELECT count(*) as cnt FROM customers WHERE tier = 'enterprise';"
        res = await sandbox.execute_sql(query, schema_ddl=ddl)
        assert res.success is True
        assert res.exit_code == 0
        assert "cnt" in res.stdout
        assert res.parsed_output["count"] == 1
        assert res.parsed_output["rows"][0][0] == 1

    @pytest.mark.anyio
    async def test_fastapi_sandbox_execution(self, sandbox):
        api_code = (
            "from pydantic import BaseModel\n\n"
            "class Metric(BaseModel):\n    name: str\n    value: float\n\n"
            "@app.get('/metrics')\ndef get_metrics():\n    return {'status': 'healthy', 'count': 42}\n\n"
            "@app.post('/metrics')\ndef add_metric(m: Metric):\n    return {'received': m.name, 'value': m.value}\n"
        )
        reqs = [
            {"method": "GET", "url": "/metrics", "expected_status": 200},
            {"method": "POST", "url": "/metrics", "json": {"name": "retention", "value": 0.85}, "expected_status": 200},
            {"method": "GET", "url": "/nonexistent", "expected_status": 404},
        ]
        res = await sandbox.execute_fastapi(api_code, reqs)
        assert res.success is True
        assert res.exit_code == 0
        assert res.verified is True
        assert len(res.parsed_output) == 3

    @pytest.mark.anyio
    async def test_react_component_validation(self, sandbox):
        component_code = (
            "import React, { useState, useEffect } from 'react';\n\n"
            "export default function GrowthDashboard({ initialKpi }) {\n"
            "    const [kpi, setKpi] = useState(initialKpi);\n"
            "    useEffect(() => {\n"
            "        console.log('Mounted');\n"
            "    }, []);\n"
            "    return (\n"
            "        <div className='dashboard'>\n"
            "            <h1>Metrics: {kpi}</h1>\n"
            "            <button onClick={() => setKpi(kpi + 1)}>Increment</button>\n"
            "        </div>\n"
            "    );\n"
            "}\n"
        )
        res = await sandbox.execute_react(component_code)
        assert res.success is True
        assert res.verified is True
        assert "useState" in res.parsed_output["hooks_detected"]
        assert "useEffect" in res.parsed_output["hooks_detected"]

    @pytest.mark.anyio
    async def test_cpp_sandbox_validation(self, sandbox):
        cpp_code = (
            "#include <iostream>\n"
            "#include <string>\n"
            "#include <algorithm>\n\n"
            "std::string reverseString(std::string s) {\n"
            "    std::reverse(s.begin(), s.end());\n"
            "    return s;\n"
            "}\n\n"
            "int main() {\n"
            "    std::cout << reverseString(\"Growth\") << std::endl;\n"
            "    return 0;\n"
            "}\n"
        )
        res = await sandbox.execute_cpp(cpp_code)
        assert res.success is True
        assert res.verified is True


# ==============================================================================
# 2. All 12 First-Class Coding Capabilities
# ==============================================================================

class TestCodingAgentCapabilities:
    """Verify each of the 12 specialized coding capabilities."""

    @pytest.mark.anyio
    async def test_01_code_generation(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.CODE_GENERATION,
            prompt="Write a Python function to reverse a string.",
            language=ExecutionLanguage.PYTHON,
            execute_in_sandbox=True,
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.CODE_GENERATION
        assert res.verified is True
        assert res.execution_result is not None
        assert res.execution_result.exit_code == 0

    @pytest.mark.anyio
    async def test_02_code_explanation(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.CODE_EXPLANATION,
            prompt="Explain quicksort partitioning logic.",
            code_snippet="def partition(arr, low, high): pass",
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.CODE_EXPLANATION
        assert "Complexity" in res.explanation

    @pytest.mark.anyio
    async def test_03_debugging(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.DEBUGGING,
            prompt="IndexError in binary search edge case",
            language=ExecutionLanguage.PYTHON,
            execute_in_sandbox=True,
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.DEBUGGING
        assert res.verified is True
        assert res.execution_result.exit_code == 0

    @pytest.mark.anyio
    async def test_04_refactoring(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.REFACTORING,
            prompt="Refactor loop accumulator into generator expression",
            language=ExecutionLanguage.PYTHON,
            execute_in_sandbox=True,
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.REFACTORING
        assert res.verified is True

    @pytest.mark.anyio
    async def test_05_optimization(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.OPTIMIZATION,
            prompt="Optimize duplicate search from O(N^2) to O(N)",
            language=ExecutionLanguage.PYTHON,
            execute_in_sandbox=True,
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.OPTIMIZATION
        assert "O(N)" in res.explanation
        assert res.verified is True

    @pytest.mark.anyio
    async def test_06_code_review(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.CODE_REVIEW,
            prompt="Security and quality audit",
            code_snippet="def store_user(password):\n    hashed = md5(password)\n    cursor.execute('SELECT * FROM users')\n",
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.CODE_REVIEW
        assert len(res.review_findings) >= 2
        severities = [f["severity"] for f in res.review_findings]
        assert "HIGH" in severities  # MD5 vulnerability caught

    @pytest.mark.anyio
    async def test_07_test_generation(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.TEST_GENERATION,
            prompt="Generate unit tests for addition utility",
            execute_in_sandbox=True,
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.TEST_GENERATION
        assert len(res.test_cases) >= 3
        assert res.verified is True

    @pytest.mark.anyio
    async def test_08_architecture(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.ARCHITECTURE,
            prompt="Design scalable event-driven ingestion pipeline",
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.ARCHITECTURE
        assert "Distributed Pipeline" in res.explanation

    @pytest.mark.anyio
    async def test_09_repository_analysis(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.REPOSITORY_ANALYSIS,
            prompt="Inspect current workspace",
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.REPOSITORY_ANALYSIS
        assert "Workspace Root" in res.explanation
        assert "FastAPI" in res.explanation or "React" in res.explanation

    @pytest.mark.anyio
    async def test_10_dependency_analysis(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.DEPENDENCY_ANALYSIS,
            prompt="Audit backend dependencies",
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.DEPENDENCY_ANALYSIS
        assert "requirements.txt" in res.explanation

    @pytest.mark.anyio
    async def test_11_api_implementation(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.API_IMPLEMENTATION,
            prompt="Create items endpoint with schema",
            language=ExecutionLanguage.FASTAPI,
            execute_in_sandbox=True,
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.API_IMPLEMENTATION
        assert res.verified is True
        assert res.execution_result.exit_code == 0

    @pytest.mark.anyio
    async def test_12_database_implementation(self, agent):
        req = CodingAgentRequest(
            capability=CodingCapability.DATABASE_IMPLEMENTATION,
            prompt="Design relational orders schema with user foreign keys",
            language=ExecutionLanguage.SQL,
            execute_in_sandbox=True,
        )
        res = await agent.handle_request(req)
        assert res.capability == CodingCapability.DATABASE_IMPLEMENTATION
        assert res.verified is True
        assert res.execution_result.parsed_output is not None


# ==============================================================================
# 3. 9-Phase Repository Lifecycle & Ground Truth Tests
# ==============================================================================

class TestRepositoryLifecyclePipeline:
    """Test strict 9-phase repository task execution and real-world ground truth."""

    def test_repository_inspect_ground_truth(self, repo_engine):
        insp = repo_engine.inspect()
        assert insp.total_files > 50
        assert "FastAPI" in insp.detected_frameworks
        assert "React" in insp.detected_frameworks
        assert "Python" in insp.languages_detected
        assert "backend/requirements.txt" in insp.package_manifests
        assert "frontend/package.json" in insp.package_manifests

    def test_repository_full_9_phase_lifecycle(self, repo_engine):
        task_desc = "Verify and test Phase 1 relevance filter invariant."
        summary = repo_engine.execute_lifecycle(
            task_description=task_desc,
            target_files=["backend/app/retrieval/relevance.py"],
            test_target="backend/tests/test_phase2_model_platform.py -k test_llm_request_contracts",
        )
        assert summary.all_passed is True
        assert summary.build_verified is True
        assert summary.test_verified is True
        assert len(summary.phases_executed) == 9

        phase_names = [p.phase.value for p in summary.phases_executed]
        assert phase_names == [
            RepoTaskPhase.INSPECT.value,
            RepoTaskPhase.UNDERSTAND.value,
            RepoTaskPhase.PLAN.value,
            RepoTaskPhase.MODIFY.value,
            RepoTaskPhase.BUILD.value,
            RepoTaskPhase.TEST.value,
            RepoTaskPhase.FIX.value,
            RepoTaskPhase.RETEST.value,
            RepoTaskPhase.REVIEW.value,
        ]

    @pytest.mark.anyio
    async def test_no_execution_claim_without_testing(self, agent):
        """Verify epistemic integrity: never claim code works if it failed in the sandbox."""
        failing_code = "def broken():\n    raise ZeroDivisionError('Intentional fail')\n\nbroken()"
        req = CodingAgentRequest(
            capability=CodingCapability.CODE_GENERATION,
            prompt="Run failing code",
            code_snippet=failing_code,
            language=ExecutionLanguage.PYTHON,
            execute_in_sandbox=True,
        )
        res = await agent.handle_request(req)
        assert res.verified is False
        assert res.execution_result.exit_code != 0
        assert "ZeroDivisionError" in res.execution_result.stderr
