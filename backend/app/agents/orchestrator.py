"""Agent Orchestrator coordinating retrieval, prompt selection, inference, artifact extraction, and citations."""

import re
import json
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import bleach

from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.config import settings
from app.db.models import Session as SessionModel, Message as MessageModel, Artifact as ArtifactModel
from app.api.schemas import MessageResponse, CitationSchema, ArtifactSummary
from app.agents.prompts import get_skill_prompt, REFUSAL_MESSAGE
from app.models.provider import get_llm_provider
from app.retrieval.retriever import retrieve_evidence, RetrievalResult

logger = logging.getLogger(__name__)

# Permitted HTML tags and attributes for operational sandboxed artifacts
ALLOWED_HTML_TAGS = [
    "div", "span", "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
    "strong", "em", "b", "i", "code", "pre", "hr", "br",
    "button", "input", "label", "form", "section", "article", "blockquote",
    "header", "footer", "main", "nav", "svg", "path"
]

ALLOWED_HTML_ATTRS = {
    "*": ["class", "id", "style", "title", "role"],
    "input": ["type", "value", "placeholder", "checked", "disabled", "name"],
    "button": ["type", "disabled", "name", "value"],
    "a": ["href", "title", "target", "rel"],
}

ARTIFACT_REGEX = re.compile(
    r'<artifact\s+type="(?P<type>[^"]+)"\s+title="(?P<title>[^"]*)">(?P<content>.*?)</artifact>',
    re.DOTALL | re.IGNORECASE
)


from bleach.css_sanitizer import CSSSanitizer

_css_sanitizer = CSSSanitizer()

def sanitize_artifact_content(raw_html: str) -> str:
    """Sanitize LLM-generated HTML artifact content using bleach whitelist and CSS sanitizer."""
    return bleach.clean(
        raw_html,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRS,
        css_sanitizer=_css_sanitizer,
        strip=True
    )


class AgentOrchestrator:
    """Multi-turn bounded agent orchestrator coordinating RAG retrieval, epistemic gate, and skill generation."""

    def __init__(self, db: SQLAlchemySession):
        self.db = db

    def execute_turn(
        self,
        session_id: str,
        content: str,
        mode: str = "research",
        provider_override: Optional[str] = None,
    ) -> MessageResponse:
        """Execute a full conversational turn for a session with grounded evidence checks."""
        start_time = time.perf_counter()

        # 1. Verify session exists
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session with ID '{session_id}' not found")

        # 2. Fetch recent conversation history for multi-turn context (last 6 messages)
        recent_messages = (
            self.db.query(MessageModel)
            .filter(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.desc())
            .limit(6)
            .all()
        )
        # Reverse to chronological order
        history = [
            {"role": m.role, "content": m.content}
            for m in reversed(recent_messages)
        ]

        # 3. Persist incoming user message
        user_msg = MessageModel(
            session_id=session_id,
            role="user",
            content=content,
            mode=mode,
            model="user",
        )
        self.db.add(user_msg)
        self.db.commit()

        # 4. Perform grounded retrieval against indexed transcript chunks
        retrieval_res: RetrievalResult = retrieve_evidence(query=content, db=self.db, top_k=4)

        # 5. Epistemic Gate Check: Refusal when similarity is below threshold or query is out-of-domain
        if not retrieval_res.grounded or not retrieval_res.evidence:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            assistant_msg = MessageModel(
                session_id=session_id,
                role="assistant",
                content=REFUSAL_MESSAGE,
                mode=mode,
                model="epistemic-gate-v2",
                latency_ms=latency_ms,
                citations="[]",
            )
            self.db.add(assistant_msg)
            session.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(assistant_msg)

            return MessageResponse(
                id=assistant_msg.id,
                session_id=session_id,
                role=assistant_msg.role,
                content=assistant_msg.content,
                mode=assistant_msg.mode,
                model=assistant_msg.model,
                latency_ms=assistant_msg.latency_ms,
                citations=[],
                artifacts=[],
                created_at=assistant_msg.created_at.isoformat() if assistant_msg.created_at else None,
            )

        # 6. Format retrieved context block
        context_parts = []
        citations: List[CitationSchema] = []
        for ev in retrieval_res.evidence:
            context_parts.append(
                f"[Source ID: {ev.chunk_id}] Guest: {ev.guest} | Episode: {ev.title}\n{ev.excerpt}"
            )
            citations.append(
                CitationSchema(
                    chunk_id=ev.chunk_id,
                    guest=ev.guest,
                    title=ev.title,
                    similarity=round(ev.similarity, 4),
                    excerpt=ev.excerpt,
                )
            )
        context_str = "\n\n---\n\n".join(context_parts)

        # 7. Prompt selection & LLM generation
        system_prompt = get_skill_prompt(mode)
        provider = get_llm_provider(override=provider_override)

        raw_llm_response = provider.generate(
            system_prompt=system_prompt,
            user_prompt=content,
            context=context_str,
            history=history,
        )

        # 8. Artifact parsing and multi-stage sanitization
        extracted_artifacts: List[ArtifactModel] = []
        artifact_summaries: List[ArtifactSummary] = []

        def artifact_replacer(match):
            art_type = match.group("type").strip().lower()
            art_title = match.group("title").strip() or "Growth Artifact"
            raw_body = match.group("content").strip()
            clean_body = sanitize_artifact_content(raw_body)

            art_record = ArtifactModel(
                session_id=session_id,
                artifact_type=art_type,
                title=art_title,
                raw_content=raw_body,
                sanitized_content=clean_body,
                status="sanitized",
            )
            extracted_artifacts.append(art_record)
            return f"\n\n> 🛠️ **Generated Operational Artifact**: *{art_title}* (Rendered in Growth Canvas)\n"

        cleaned_content = ARTIFACT_REGEX.sub(artifact_replacer, raw_llm_response)

        # 9. Persist assistant message and link artifacts
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        assistant_msg = MessageModel(
            session_id=session_id,
            role="assistant",
            content=cleaned_content.strip(),
            mode=mode,
            model=provider.get_model_name(),
            latency_ms=latency_ms,
            citations=json.dumps([c.model_dump() for c in citations]),
        )
        self.db.add(assistant_msg)
        self.db.flush()  # Allocate assistant_msg.id

        for art in extracted_artifacts:
            art.message_id = assistant_msg.id
            self.db.add(art)
            self.db.flush()
            artifact_summaries.append(
                ArtifactSummary(
                    id=art.id,
                    artifact_type=art.artifact_type,
                    title=art.title,
                    status=art.status,
                    created_at=art.created_at.isoformat() if art.created_at else None,
                )
            )

        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(assistant_msg)

        return MessageResponse(
            id=assistant_msg.id,
            session_id=session_id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            mode=assistant_msg.mode,
            model=assistant_msg.model,
            latency_ms=assistant_msg.latency_ms,
            citations=citations,
            artifacts=artifact_summaries,
            created_at=assistant_msg.created_at.isoformat() if assistant_msg.created_at else None,
        )
