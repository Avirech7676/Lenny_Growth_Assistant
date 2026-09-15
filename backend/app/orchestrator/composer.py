"""Response Composer for AI Orchestrator.

Assembles and formats the final unified response:
- Growth Canvas artifact extraction, sanitization, and replacement
- Citation metadata structuring
- Multi-step telemetry formatting
"""

import re
from typing import List, Dict, Any, Tuple
from app.utils.sanitize import sanitize_artifact_content
from app.orchestrator.types import ExecutionPlan, VerificationResult, Capability

ARTIFACT_REGEX = re.compile(
    r'<artifact\s+type="(?P<type>[^"]+)"\s+title="(?P<title>[^"]*)">(?P<content>.*?)</artifact>',
    re.DOTALL | re.IGNORECASE
)


class ResponseComposer:
    """Assembles final output, renders interactive artifacts, and injects verification metadata."""

    def compose(
        self,
        raw_text: str,
        plan: ExecutionPlan,
        citations: List[Dict[str, Any]],
        verification: Optional[VerificationResult] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Process artifacts, format citations, and build cleaned final content."""
        extracted_artifacts: List[Dict[str, Any]] = []

        def artifact_replacer(match):
            art_type = match.group("type").strip().lower()
            art_title = match.group("title").strip() or "Growth Artifact"
            raw_body = match.group("content").strip()
            clean_body = sanitize_artifact_content(raw_body)

            extracted_artifacts.append({
                "artifact_type": art_type,
                "title": art_title,
                "raw_content": raw_body,
                "sanitized_content": clean_body,
                "status": "sanitized",
            })
            return f"\n\n> 🛠️ **Generated Operational Artifact**: *{art_title}* (Rendered in Growth Canvas)\n"

        cleaned_content = ARTIFACT_REGEX.sub(artifact_replacer, raw_text).strip()

        return cleaned_content, extracted_artifacts
