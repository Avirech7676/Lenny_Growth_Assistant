"""Coding Agent — Repository Inspector & Code Intelligence Service.

Provides:
- Directory tree inspection (workspace-scoped, path-traversal safe)
- File read with syntax detection
- Multi-step code plan: write → validate → test → explain
- Syntax validation (Python AST, JSON)
- Test runner (pytest subprocess, isolated)
- Git awareness (branch, last commit, diff summary)
"""

import ast
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Maximum safe file size to read in bytes
MAX_FILE_READ_BYTES = 32_000
# Depth limit for directory traversal
MAX_TREE_DEPTH = 4
# Forbidden top-level paths (never allow traversal above workspace root)
_FORBIDDEN_SEGMENTS = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".mypy_cache"}


# ─── Data Classes ─────────────────────────────────────────────────────────────

class FileNode:
    """Represents a single file or directory in a workspace tree."""
    __slots__ = ["name", "path", "is_dir", "size", "children", "language"]

    def __init__(self, name: str, path: str, is_dir: bool, size: int = 0,
                 children: Optional[List["FileNode"]] = None, language: str = ""):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.size = size
        self.children = children or []
        self.language = language

    def to_dict(self) -> dict:
        d = {"name": self.name, "path": self.path, "is_dir": self.is_dir}
        if not self.is_dir:
            d["size"] = self.size
            d["language"] = self.language
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


class SyntaxValidationResult:
    """Result of a syntax validation check."""
    __slots__ = ["valid", "language", "errors", "warnings", "lines"]

    def __init__(self, valid: bool, language: str, errors: List[str],
                 warnings: List[str], lines: int):
        self.valid = valid
        self.language = language
        self.errors = errors
        self.warnings = warnings
        self.lines = lines

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "language": self.language,
            "errors": self.errors,
            "warnings": self.warnings,
            "lines": self.lines,
        }


class TestRunResult:
    """Result of running the test suite."""
    __slots__ = ["success", "passed", "failed", "errors", "output", "duration_ms"]

    def __init__(self, success: bool, passed: int, failed: int, errors: int,
                 output: str, duration_ms: float):
        self.success = success
        self.passed = passed
        self.failed = failed
        self.errors = errors
        self.output = output
        self.duration_ms = duration_ms

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "output": self.output[:4000],
            "duration_ms": round(self.duration_ms, 2),
        }


class CodePlan:
    """A structured multi-step plan for implementing a coding task."""
    __slots__ = ["goal", "steps", "estimated_files", "complexity", "notes"]

    def __init__(self, goal: str, steps: List[str], estimated_files: List[str],
                 complexity: str, notes: str = ""):
        self.goal = goal
        self.steps = steps
        self.estimated_files = estimated_files
        self.complexity = complexity
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": self.steps,
            "estimated_files": self.estimated_files,
            "complexity": self.complexity,
            "notes": self.notes,
        }

    def format_for_llm(self) -> str:
        lines = [f"CODING TASK: {self.goal}", f"COMPLEXITY: {self.complexity}", ""]
        lines.append("IMPLEMENTATION STEPS:")
        for i, step in enumerate(self.steps, 1):
            lines.append(f"  {i}. {step}")
        if self.estimated_files:
            lines.append("\nFILES TO CREATE/MODIFY:")
            for f in self.estimated_files:
                lines.append(f"  - {f}")
        if self.notes:
            lines.append(f"\nNOTES: {self.notes}")
        return "\n".join(lines)


# ─── Extension → Language Map ─────────────────────────────────────────────────
_EXT_LANGUAGE = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "jsx", ".tsx": "tsx", ".java": "java", ".go": "go",
    ".rs": "rust", ".cpp": "c++", ".c": "c", ".cs": "csharp",
    ".rb": "ruby", ".php": "php", ".sh": "bash", ".sql": "sql",
    ".html": "html", ".css": "css", ".json": "json", ".yaml": "yaml",
    ".yml": "yaml", ".toml": "toml", ".md": "markdown", ".tf": "terraform",
    ".dockerfile": "dockerfile", ".env": "env",
}


def _detect_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    name = Path(path).name.lower()
    if name == "dockerfile":
        return "dockerfile"
    if name in (".env", ".env.local", ".env.production"):
        return "env"
    return _EXT_LANGUAGE.get(ext, "text")


def _safe_path(workspace_root: str, requested: str) -> Optional[str]:
    """Resolve and validate a path stays within workspace_root."""
    try:
        root = Path(workspace_root).resolve()
        target = (root / requested).resolve()
        target.relative_to(root)  # raises ValueError if outside
        return str(target)
    except (ValueError, Exception):
        return None


# ─── Repository Inspector ────────────────────────────────────────────────────

class RepositoryInspector:
    """Workspace-scoped repository inspection for coding intelligence."""

    def __init__(self, workspace_root: str):
        self.workspace_root = str(Path(workspace_root).resolve())

    def directory_tree(self, relative_path: str = ".", depth: int = 3) -> Optional[FileNode]:
        """Return a FileNode tree for the given relative path (depth-limited)."""
        depth = min(depth, MAX_TREE_DEPTH)
        safe = _safe_path(self.workspace_root, relative_path)
        if not safe:
            logger.warning("Path traversal blocked: %s", relative_path)
            return None

        target = Path(safe)
        if not target.exists():
            return None

        return self._build_node(target, depth)

    def _build_node(self, path: Path, depth: int) -> FileNode:
        name = path.name or str(path)
        rel = str(path.relative_to(self.workspace_root))
        is_dir = path.is_dir()

        if not is_dir:
            size = path.stat().st_size if path.exists() else 0
            return FileNode(name=name, path=rel, is_dir=False, size=size,
                            language=_detect_language(str(path)))

        children: List[FileNode] = []
        if depth > 0:
            try:
                for child in sorted(path.iterdir()):
                    if child.name.startswith(".") or child.name in _FORBIDDEN_SEGMENTS:
                        continue
                    children.append(self._build_node(child, depth - 1))
            except PermissionError:
                pass

        return FileNode(name=name, path=rel, is_dir=True, children=children)

    def read_file(self, relative_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Read a file safely. Returns (content, error)."""
        safe = _safe_path(self.workspace_root, relative_path)
        if not safe:
            return None, "Path traversal blocked"

        path = Path(safe)
        if not path.exists():
            return None, f"File not found: {relative_path}"
        if not path.is_file():
            return None, f"Not a file: {relative_path}"

        size = path.stat().st_size
        if size > MAX_FILE_READ_BYTES:
            return None, f"File too large ({size // 1024}KB). Max: {MAX_FILE_READ_BYTES // 1024}KB"

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return content, None
        except PermissionError:
            return None, f"Permission denied: {relative_path}"
        except Exception as exc:
            return None, f"Read error: {exc}"

    def git_context(self) -> Dict[str, Any]:
        """Return basic git context: branch, last commit, staged/unstaged file counts."""
        ctx: Dict[str, Any] = {"available": False}
        git_dir = Path(self.workspace_root) / ".git"
        if not git_dir.exists():
            return ctx

        try:
            branch = subprocess.run(
                ["git", "-C", self.workspace_root, "branch", "--show-current"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()

            last_commit = subprocess.run(
                ["git", "-C", self.workspace_root, "log", "-1", "--oneline"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()

            status_out = subprocess.run(
                ["git", "-C", self.workspace_root, "status", "--porcelain"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()

            changed_files = [line.strip() for line in status_out.splitlines() if line.strip()]

            ctx.update({
                "available": True,
                "branch": branch,
                "last_commit": last_commit,
                "changed_files_count": len(changed_files),
                "changed_files": changed_files[:10],
            })
        except Exception as exc:
            ctx["error"] = str(exc)

        return ctx

    def format_tree_for_llm(self, node: FileNode, indent: int = 0) -> str:
        """Format a FileNode tree as an ASCII tree string for LLM context."""
        prefix = "  " * indent
        if node.is_dir:
            lines = [f"{prefix}📁 {node.name}/"]
            for child in node.children[:20]:  # cap at 20 children per dir
                lines.append(self.format_tree_for_llm(child, indent + 1))
        else:
            lang = f" [{node.language}]" if node.language and node.language != "text" else ""
            size_str = f" ({node.size // 1024}KB)" if node.size > 1024 else ""
            lines = [f"{prefix}📄 {node.name}{lang}{size_str}"]
        return "\n".join(lines)


# ─── Syntax Validator ─────────────────────────────────────────────────────────

class SyntaxValidator:
    """Multi-language syntax validator using language-appropriate parsers."""

    def validate(self, code: str, filename: str) -> SyntaxValidationResult:
        """Validate code syntax for the detected language."""
        language = _detect_language(filename)
        lines = code.count("\n") + 1

        if language == "python":
            return self._validate_python(code, lines)
        elif language == "json":
            return self._validate_json(code, lines)
        else:
            # For other languages: basic heuristic checks only
            return SyntaxValidationResult(
                valid=True, language=language, errors=[],
                warnings=["Full syntax validation not available for this language; manual review recommended."],
                lines=lines,
            )

    def _validate_python(self, code: str, lines: int) -> SyntaxValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        try:
            ast.parse(code)
        except SyntaxError as exc:
            errors.append(f"SyntaxError at line {exc.lineno}: {exc.msg}")
        except Exception as exc:
            errors.append(f"Parse error: {exc}")

        # Basic quality checks
        if "import *" in code:
            warnings.append("Avoid wildcard imports (import *)")
        if re.search(r'except\s*:', code):
            warnings.append("Bare 'except:' clause found — prefer 'except Exception as e:'")
        if "TODO" in code or "FIXME" in code:
            warnings.append("TODO/FIXME markers present — resolve before production")

        return SyntaxValidationResult(
            valid=len(errors) == 0, language="python",
            errors=errors, warnings=warnings, lines=lines,
        )

    def _validate_json(self, code: str, lines: int) -> SyntaxValidationResult:
        errors: List[str] = []
        try:
            json.loads(code)
        except json.JSONDecodeError as exc:
            errors.append(f"JSONDecodeError at line {exc.lineno}, col {exc.colno}: {exc.msg}")
        return SyntaxValidationResult(
            valid=len(errors) == 0, language="json",
            errors=errors, warnings=[], lines=lines,
        )


# ─── Test Runner ─────────────────────────────────────────────────────────────

class TestRunner:
    """Safe pytest subprocess runner with timeout enforcement."""

    def __init__(self, workspace_root: str, timeout_seconds: int = 60):
        self.workspace_root = workspace_root
        self.timeout_seconds = timeout_seconds

    def run_tests(self, test_path: str = ".", extra_args: Optional[List[str]] = None) -> TestRunResult:
        """Run pytest in a subprocess. Returns structured TestRunResult."""
        safe = _safe_path(self.workspace_root, test_path)
        if not safe:
            return TestRunResult(
                success=False, passed=0, failed=0, errors=1,
                output="Path traversal blocked — cannot run tests outside workspace.",
                duration_ms=0.0,
            )

        cmd = [sys.executable, "-m", "pytest", safe, "-q", "--tb=short", "--no-header"]
        if extra_args:
            cmd.extend(extra_args)

        t0 = time.perf_counter()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        except subprocess.TimeoutExpired:
            return TestRunResult(
                success=False, passed=0, failed=0, errors=1,
                output=f"Test run timed out after {self.timeout_seconds}s.",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return TestRunResult(
                success=False, passed=0, failed=0, errors=1,
                output=f"Failed to launch test runner: {exc}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        duration_ms = (time.perf_counter() - t0) * 1000
        output = (result.stdout + result.stderr)[:8000]

        # Parse summary line: "3 passed, 1 failed, 0 errors"
        passed = failed = errors_count = 0
        summary_match = re.search(
            r'(\d+) passed(?:,\s*(\d+) failed)?(?:,\s*(\d+) error)?', output
        )
        if summary_match:
            passed = int(summary_match.group(1) or 0)
            failed = int(summary_match.group(2) or 0)
            errors_count = int(summary_match.group(3) or 0)
        elif "failed" in output:
            fail_match = re.search(r'(\d+) failed', output)
            failed = int(fail_match.group(1)) if fail_match else 1

        return TestRunResult(
            success=result.returncode == 0,
            passed=passed,
            failed=failed,
            errors=errors_count,
            output=output,
            duration_ms=duration_ms,
        )


# ─── Code Planner ─────────────────────────────────────────────────────────────

class CodePlanner:
    """Generates structured multi-step implementation plans from natural language goals."""

    _COMPLEXITY_KEYWORDS = {
        "simple": ["fix", "add a", "rename", "update", "correct", "typo", "comment"],
        "moderate": ["implement", "create", "build", "extend", "refactor", "optimize"],
        "complex": ["architect", "design system", "migrate", "full", "entire", "production"],
    }

    def plan(self, goal: str, repo_context: Optional[str] = None) -> CodePlan:
        """Generate a CodePlan from a natural language goal."""
        complexity = self._estimate_complexity(goal)
        steps = self._generate_steps(goal, complexity)
        files = self._estimate_files(goal, repo_context)
        notes = self._generate_notes(goal, repo_context)

        return CodePlan(
            goal=goal,
            steps=steps,
            estimated_files=files,
            complexity=complexity,
            notes=notes,
        )

    def _estimate_complexity(self, goal: str) -> str:
        g = goal.lower()
        for level, keywords in self._COMPLEXITY_KEYWORDS.items():
            if any(k in g for k in keywords):
                return level
        return "moderate"

    def _generate_steps(self, goal: str, complexity: str) -> List[str]:
        g = goal.lower()

        if "test" in g or "unit test" in g:
            return [
                "Identify functions/classes to test",
                "Write test cases covering happy path, edge cases, and error paths",
                "Add fixtures and mocks for external dependencies",
                "Run test suite and verify all pass",
                "Document test coverage gaps",
            ]

        if "debug" in g or "fix" in g or "error" in g:
            return [
                "Reproduce the error locally",
                "Identify root cause from stack trace or logs",
                "Implement minimal fix",
                "Add regression test for this exact case",
                "Verify no other tests broken",
            ]

        if complexity == "simple":
            return [
                "Identify the target file(s) and function(s)",
                "Implement the change",
                "Verify no adjacent tests break",
            ]

        if complexity == "complex":
            return [
                "Design high-level architecture and data models",
                "Define interfaces and API contracts",
                "Implement core modules with error handling",
                "Wire modules together with dependency injection",
                "Write unit tests for each module",
                "Write integration tests for critical paths",
                "Document public API and edge cases",
                "Review for security, performance, and maintainability",
            ]

        # Default: moderate
        return [
            "Understand requirements and existing code patterns",
            "Design the implementation approach",
            "Implement with error handling and type annotations",
            "Write unit tests for the new code",
            "Verify existing tests still pass",
            "Add inline documentation",
        ]

    def _estimate_files(self, goal: str, repo_context: Optional[str]) -> List[str]:
        """Heuristically estimate which files will need to be touched."""
        files: List[str] = []
        g = goal.lower()

        if "api" in g or "endpoint" in g or "route" in g:
            files.extend(["app/api/routes.py", "app/api/schemas.py"])
        if "test" in g:
            files.append("tests/test_*.py")
        if "model" in g or "database" in g or "schema" in g:
            files.extend(["app/db/models.py", "migrations/"])
        if "frontend" in g or "ui" in g or "component" in g:
            files.extend(["frontend/src/components/", "frontend/src/App.jsx"])

        return files[:6]

    def _generate_notes(self, goal: str, repo_context: Optional[str]) -> str:
        notes: List[str] = []
        g = goal.lower()

        if "async" in g or "stream" in g:
            notes.append("Use async/await throughout for non-blocking I/O")
        if "security" in g or "auth" in g:
            notes.append("Apply input validation and avoid exposing sensitive data")
        if repo_context and "fastapi" in repo_context.lower():
            notes.append("Follow FastAPI dependency injection patterns")
        if repo_context and "react" in repo_context.lower():
            notes.append("Use React hooks and functional components")

        return " | ".join(notes)


# ─── Coding Agent ─────────────────────────────────────────────────────────────

class CodingAgent:
    """Master coding intelligence agent combining inspection, planning, validation, and testing."""

    def __init__(self, workspace_root: str):
        self.inspector = RepositoryInspector(workspace_root)
        self.validator = SyntaxValidator()
        self.runner = TestRunner(workspace_root)
        self.planner = CodePlanner()
        self.workspace_root = workspace_root

    def build_context_for_llm(self, goal: str, target_files: Optional[List[str]] = None) -> str:
        """Build rich coding context for the LLM: repo tree + git state + file contents."""
        parts: List[str] = []

        # 1. Repository tree overview
        tree = self.inspector.directory_tree(".", depth=2)
        if tree:
            parts.append("REPOSITORY STRUCTURE:\n" + self.inspector.format_tree_for_llm(tree))

        # 2. Git context
        git_ctx = self.inspector.git_context()
        if git_ctx.get("available"):
            parts.append(
                f"GIT CONTEXT: branch={git_ctx['branch']} | "
                f"last_commit={git_ctx['last_commit']} | "
                f"changed_files={git_ctx['changed_files_count']}"
            )

        # 3. Target file contents
        if target_files:
            for rel_path in target_files[:4]:
                content, err = self.inspector.read_file(rel_path)
                if content:
                    lang = _detect_language(rel_path)
                    parts.append(
                        f"\nFILE: {rel_path} ({lang})\n```{lang}\n{content[:6000]}\n```"
                    )
                elif err:
                    parts.append(f"\nFILE: {rel_path} — could not read: {err}")

        # 4. Implementation plan
        repo_ctx = "\n".join(parts[:500])
        plan = self.planner.plan(goal, repo_context=repo_ctx)
        parts.append("\nIMPLEMENTATION PLAN:\n" + plan.format_for_llm())

        return "\n\n".join(parts)

    def validate_code_snippet(self, code: str, filename: str) -> SyntaxValidationResult:
        return self.validator.validate(code, filename)

    def run_tests(self, test_path: str = ".") -> TestRunResult:
        return self.runner.run_tests(test_path)


# ─── Singleton Factory ────────────────────────────────────────────────────────

_WORKSPACE_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

_CODING_AGENT: Optional[CodingAgent] = None


def get_coding_agent(workspace_root: Optional[str] = None) -> CodingAgent:
    """Get or create the singleton CodingAgent for the current workspace."""
    global _CODING_AGENT
    if _CODING_AGENT is None or (workspace_root and workspace_root != _CODING_AGENT.workspace_root):
        root = workspace_root or _WORKSPACE_ROOT
        _CODING_AGENT = CodingAgent(workspace_root=root)
    return _CODING_AGENT
