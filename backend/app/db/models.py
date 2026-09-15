"""SQLAlchemy ORM models for conversational sessions, messages, transcripts, and artifacts."""

from datetime import datetime, timezone
import uuid
import json
from typing import List, Optional, Any, Dict
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Float, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class Session(Base):
    """Conversational session entity storing chat threads and artifacts."""

    __tablename__ = "sessions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
        doc="Unique UUID primary key",
    )
    title = Column(
        String(255),
        nullable=False,
        default="New Growth Session",
        doc="Human-readable title or generated topic summary",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        doc="Timestamp when session was initiated",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        doc="Timestamp of latest message in this session",
    )
    meta_info = Column(
        Text,
        nullable=True,
        default="{}",
        doc="JSON-encoded session metadata",
    )

    # Relationships
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc()",
    )
    artifacts = relationship(
        "Artifact",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Artifact.created_at.desc()",
    )
    uploaded_documents = relationship(
        "UploadedDocument",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="UploadedDocument.created_at.desc()",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": json.loads(self.meta_info) if self.meta_info else {},
        }

    def __repr__(self) -> str:
        return f"<Session(id='{self.id}', title='{self.title}')>"


class Message(Base):
    """Message entity representing user prompts, assistant answers, and citations."""

    __tablename__ = "messages"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
        doc="Unique UUID primary key",
    )
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key referencing Session.id",
    )
    role = Column(
        String(32),
        nullable=False,
        doc="'user', 'assistant', or 'system'",
    )
    content = Column(
        Text,
        nullable=False,
        doc="Markdown content of the message",
    )
    mode = Column(
        String(64),
        nullable=False,
        default="research",
        doc="'research', 'ship30', 'experiment', 'playbook'",
    )
    model = Column(
        String(64),
        nullable=False,
        default="llama3.2:latest",
        doc="Model slug used to generate response",
    )
    latency_ms = Column(
        Float,
        nullable=True,
        default=0.0,
        doc="Round-trip inference and retrieval latency in milliseconds",
    )
    citations = Column(
        Text,
        nullable=True,
        default="[]",
        doc="JSON-encoded grounding citations from retrieved transcript chunks",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        doc="Message timestamp",
    )

    # Relationships
    session = relationship("Session", back_populates="messages")
    artifacts = relationship("Artifact", back_populates="message")

    def to_dict(self) -> Dict[str, Any]:
        cits = json.loads(self.citations) if self.citations else []
        
        cap = None
        int_mode = None
        if self.mode == "coding":
            cap = "coding"
            int_mode = "real_world"
        elif self.mode == "debugging":
            cap = "debugging"
            int_mode = "real_world"
        elif self.mode == "architecture":
            cap = "architecture"
            int_mode = "real_world"
        elif self.mode == "deep_research":
            cap = "deep_research"
            int_mode = "real_world"
        elif self.mode == "search":
            cap = "web_research"
            int_mode = "real_world"
        elif self.mode == "lenny":
            cap = "lenny_research"
            int_mode = "lenny"
        elif self.mode == "chat":
            cap = "general_qa"
            int_mode = "real_world"
        else:
            has_ext = any(c.get("source_type") == "external" or c.get("url") for c in cits)
            has_lenny = any(c.get("source_type") == "transcript" for c in cits)
            if has_ext and has_lenny:
                cap = "hybrid_research"
                int_mode = "hybrid"
            elif has_ext:
                cap = "deep_research"
                int_mode = "real_world"
            elif has_lenny:
                cap = "lenny_research"
                int_mode = "lenny"
            else:
                cap = "general_qa"
                int_mode = "real_world"

        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "mode": self.mode,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "citations": cits,
            "intelligence_mode": int_mode,
            "capability": cap,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Message(id='{self.id}', session_id='{self.session_id}', role='{self.role}')>"


class Transcript(Base):
    """Podcast or newsletter transcript source entity."""

    __tablename__ = "transcripts"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    title = Column(
        String(255),
        nullable=False,
        doc="Episode title or article headline",
    )
    guest = Column(
        String(128),
        nullable=False,
        doc="Interview guest name or author",
    )
    episode_url = Column(
        String(512),
        nullable=True,
        doc="Canonical episode or newsletter link",
    )
    published_date = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    chunk_count = Column(
        Integer,
        default=0,
    )
    content_hash = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="SHA-256 hash to ensure idempotent ingestion",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    chunks = relationship(
        "TranscriptChunk",
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="TranscriptChunk.chunk_index.asc()",
    )

    def __repr__(self) -> str:
        return f"<Transcript(id='{self.id}', guest='{self.guest}', title='{self.title}')>"


class TranscriptChunk(Base):
    """Segmented transcript chunk with dense vector embedding for cosine retrieval."""

    __tablename__ = "transcript_chunks"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    transcript_id = Column(
        String(36),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(
        Integer,
        nullable=False,
    )
    content = Column(
        Text,
        nullable=False,
        doc="Raw chunk text excerpt",
    )
    # Embedding stored as JSON string for cross-database compatibility (Postgres/SQLite)
    embedding_json = Column(
        Text,
        nullable=False,
        doc="JSON serialized 768-dimensional float embedding vector",
    )
    token_count = Column(
        Integer,
        default=0,
    )
    meta_info = Column(
        Text,
        nullable=True,
        default="{}",
        doc="JSON metadata (guest, title, timestamp)",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    transcript = relationship("Transcript", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<TranscriptChunk(id='{self.id}', transcript_id='{self.transcript_id}', index={self.chunk_index})>"


class Artifact(Base):
    """Generated operational artifact (HTML widget, Markdown framework, calculator)."""

    __tablename__ = "artifacts"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id = Column(
        String(36),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    artifact_type = Column(
        String(32),
        nullable=False,
        default="html",
        doc="'html', 'markdown', 'calculator', 'checklist'",
    )
    title = Column(
        String(255),
        nullable=False,
        doc="Display title for the Growth Canvas tab",
    )
    raw_content = Column(
        Text,
        nullable=False,
        doc="Raw LLM generated content",
    )
    sanitized_content = Column(
        Text,
        nullable=False,
        doc="DOMPurified / Bleached safe content for isolated rendering",
    )
    status = Column(
        String(32),
        nullable=False,
        default="sanitized",
        doc="'sanitized', 'rejected', 'pending'",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    session = relationship("Session", back_populates="artifacts")
    message = relationship("Message", back_populates="artifacts")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "artifact_type": self.artifact_type,
            "title": self.title,
            "sanitized_content": self.sanitized_content,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Artifact(id='{self.id}', title='{self.title}', type='{self.artifact_type}')>"


class RetrievalLog(Base):
    """Observability telemetry for RAG retrieval queries."""

    __tablename__ = "retrieval_logs"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    query = Column(
        Text,
        nullable=False,
    )
    top_similarity = Column(
        Float,
        nullable=False,
    )
    chunks_count = Column(
        Integer,
        nullable=False,
    )
    latency_ms = Column(
        Float,
        nullable=False,
    )
    grounded = Column(
        Boolean,
        default=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )


class UploadedDocument(Base):
    """Uploaded document parsed and associated with a conversation session."""

    __tablename__ = "uploaded_documents"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = Column(
        String(255),
        nullable=False,
    )
    file_type = Column(
        String(50),
        nullable=False,
        default="unknown",
    )
    extracted_text = Column(
        Text,
        nullable=False,
    )
    char_count = Column(
        Integer,
        default=0,
    )
    summary = Column(
        Text,
        nullable=True,
        default="",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    session = relationship("Session", back_populates="uploaded_documents")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "char_count": self.char_count,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
