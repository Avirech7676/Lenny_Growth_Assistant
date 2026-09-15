"""Task Planner for AI Orchestrator.

Generates an executable multi-stage pipeline (ExecutionPlan) from selected capabilities:
- Deconstructs compound tasks into discrete steps
- Binds tool requirements
- Assigns model preference tiers
- Calculates latency expectations
"""

import uuid
from typing import List
from app.orchestrator.types import Capability, IntentProfile, TaskStep, ExecutionPlan


class TaskPlanner:
    """Compiles capabilities and user intent into an actionable ExecutionPlan."""

    def plan(self, query: str, capabilities: List[Capability], intent_profile: IntentProfile) -> ExecutionPlan:
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        is_compound = len(capabilities) > 1
        steps: List[TaskStep] = []
        step_id = 1

        for cap in capabilities:
            if cap == Capability.RESEARCH:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Real-World Web Research",
                    description=f"Query verified authoritative web sources for: {query[:60]}",
                    tool_required="search_engine",
                    target_model_profile="research",
                ))
                step_id += 1

            elif cap == Capability.DEEP_RESEARCH:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Deep Multi-Source Investigation",
                    description="Execute deep multi-perspective inquiry with cross-source corroboration.",
                    tool_required="deep_research_engine",
                    target_model_profile="research",
                ))
                step_id += 1

            elif cap == Capability.LENNY_RESEARCH:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Podcast Transcript Evidence Retrieval",
                    description="Extract grounded turnaround & growth frameworks from Lenny's interviews.",
                    tool_required="transcript_retriever",
                    target_model_profile="general",
                ))
                step_id += 1

            elif cap == Capability.HYBRID_TASK:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Cross-Domain Synthesis",
                    description="Synthesize podcast frameworks with 2026 real-world market intelligence.",
                    tool_required="hybrid_synthesizer",
                    target_model_profile="research",
                ))
                step_id += 1

            elif cap == Capability.CODE_REVIEW:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Code Quality & Security Audit",
                    description="Inspect source code for security vulnerabilities, bugs, and performance anti-patterns.",
                    tool_required="code_linter",
                    target_model_profile="coding",
                ))
                step_id += 1

            elif cap == Capability.DEBUGGING:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Bug Diagnosis & Root Cause Isolation",
                    description="Analyze error stack trace and formulate correct patch.",
                    tool_required="code_debugger",
                    target_model_profile="coding",
                ))
                step_id += 1

            elif cap == Capability.CODING:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Production Code Implementation",
                    description="Generate clean, type-hinted, idiomatic implementation.",
                    tool_required="code_generator",
                    target_model_profile="coding",
                ))
                step_id += 1

            elif cap == Capability.ARCHITECTURE:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="System & Schema Architecture",
                    description="Design scalable schemas, boundary interfaces, and data models.",
                    tool_required="architecture_designer",
                    target_model_profile="coding",
                ))
                step_id += 1

            elif cap == Capability.DATA_ANALYSIS:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Quantitative Metrics Analysis",
                    description="Compute cohort retention, unit economics, and growth metrics.",
                    tool_required="metrics_calculator",
                    target_model_profile="general",
                ))
                step_id += 1

            elif cap == Capability.DOCUMENT_ANALYSIS:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Document Insight Extraction",
                    description="Extract high-leverage qualitative themes and data points from document.",
                    tool_required="document_parser",
                    target_model_profile="general",
                ))
                step_id += 1

            elif cap == Capability.WRITING:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Structured Content Composition",
                    description="Compose persuasive, clear, structured written artifact (Ship 30 format).",
                    tool_required="prose_composer",
                    target_model_profile="general",
                ))
                step_id += 1

            elif cap == Capability.PLANNING:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Experiment & Execution Planning",
                    description="Formulate actionable roadmap with milestones and ICE prioritization.",
                    tool_required="roadmap_planner",
                    target_model_profile="general",
                ))
                step_id += 1

            elif cap == Capability.ARTIFACT_GENERATION:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Interactive Canvas Artifact Generation",
                    description="Generate rendered HTML/Tailwind Growth Canvas component.",
                    tool_required="canvas_builder",
                    target_model_profile="coding",
                ))
                step_id += 1

            elif cap == Capability.GENERAL_QA:
                steps.append(TaskStep(
                    step_id=step_id,
                    capability=cap,
                    name="Conceptual Explanation & Direct Answer",
                    description="Provide grounded explanation with clarity and academic precision.",
                    tool_required=None,
                    target_model_profile="fast",
                ))
                step_id += 1

        # Determine latency tier
        if Capability.DEEP_RESEARCH in capabilities:
            latency_tier = "deep"
        elif is_compound or Capability.RESEARCH in capabilities or Capability.CODING in capabilities:
            latency_tier = "standard"
        elif Capability.GENERAL_QA in capabilities and not is_compound:
            latency_tier = "fast"
        else:
            latency_tier = "standard"

        rationale = f"Constructed {len(steps)}-stage execution plan for capabilities: {', '.join([c.value for c in capabilities])}"

        return ExecutionPlan(
            plan_id=plan_id,
            capabilities=capabilities,
            steps=steps,
            is_compound=is_compound,
            estimated_latency_tier=latency_tier,
            rationale=rationale,
        )
