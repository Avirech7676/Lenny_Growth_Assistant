"""Semantic chunking engine with sliding context overlap."""

from typing import List, Dict, Any
from dataclasses import dataclass
from ingestion.parser import ParsedTranscript

@dataclass
class Chunk:
    chunk_index: int
    content: str
    token_count: int
    speaker: str
    metadata: Dict[str, Any]

def estimate_tokens(text: str) -> int:
    """Fast rule-of-thumb token estimator (approx 4 chars per token)."""
    return max(1, len(text.split()) * 4 // 3)

def chunk_transcript(
    parsed: ParsedTranscript,
    target_chunk_tokens: int = 250,
    overlap_tokens: int = 40,
) -> List[Chunk]:
    """Break a parsed transcript into overlapping semantic chunks preserving speaker context."""
    chunks: List[Chunk] = []
    current_text_segments: List[str] = []
    current_tokens: int = 0
    current_speaker: str = parsed.guest
    chunk_idx = 0

    target_chars = target_chunk_tokens * 4
    overlap_chars = overlap_tokens * 4

    for turn in parsed.dialogue_turns:
        speaker = turn["speaker"]
        speech = turn["text"]
        
        # Format segment with speaker label
        segment = f"**{speaker}:** {speech}"
        segment_tokens = estimate_tokens(segment)

        # If a single turn is massive (> target_chars), split by paragraphs
        if len(segment) > target_chars:
            paragraphs = speech.split("\n\n")
            for para in paragraphs:
                para_clean = para.strip()
                if not para_clean:
                    continue
                para_segment = f"**{speaker}:** {para_clean}"
                para_tokens = estimate_tokens(para_segment)
                
                if current_tokens + para_tokens > target_chunk_tokens and current_text_segments:
                    # Emit chunk
                    chunk_body = "\n\n".join(current_text_segments)
                    chunks.append(
                        Chunk(
                            chunk_index=chunk_idx,
                            content=chunk_body,
                            token_count=estimate_tokens(chunk_body),
                            speaker=current_speaker,
                            metadata={
                                "guest": parsed.guest,
                                "title": parsed.title,
                                "source": parsed.source,
                                "chunk_index": chunk_idx,
                            },
                        )
                    )
                    chunk_idx += 1
                    # Sliding overlap: keep last segment if it fits
                    if current_text_segments:
                        overlap_tail = current_text_segments[-1]
                        current_text_segments = [overlap_tail] if len(overlap_tail) <= overlap_chars else []
                        current_tokens = estimate_tokens("\n\n".join(current_text_segments)) if current_text_segments else 0
                    else:
                        current_text_segments = []
                        current_tokens = 0

                current_text_segments.append(para_segment)
                current_tokens += para_tokens
                current_speaker = speaker
        else:
            if current_tokens + segment_tokens > target_chunk_tokens and current_text_segments:
                # Emit chunk
                chunk_body = "\n\n".join(current_text_segments)
                chunks.append(
                    Chunk(
                        chunk_index=chunk_idx,
                        content=chunk_body,
                        token_count=estimate_tokens(chunk_body),
                        speaker=current_speaker,
                        metadata={
                            "guest": parsed.guest,
                            "title": parsed.title,
                            "source": parsed.source,
                            "chunk_index": chunk_idx,
                        },
                    )
                )
                chunk_idx += 1
                # Sliding overlap
                if current_text_segments:
                    overlap_tail = current_text_segments[-1]
                    current_text_segments = [overlap_tail] if len(overlap_tail) <= overlap_chars else []
                    current_tokens = estimate_tokens("\n\n".join(current_text_segments)) if current_text_segments else 0
                else:
                    current_text_segments = []
                    current_tokens = 0

            current_text_segments.append(segment)
            current_tokens += segment_tokens
            current_speaker = speaker

    # Final residual chunk
    if current_text_segments:
        chunk_body = "\n\n".join(current_text_segments)
        chunks.append(
            Chunk(
                chunk_index=chunk_idx,
                content=chunk_body,
                token_count=estimate_tokens(chunk_body),
                speaker=current_speaker,
                metadata={
                    "guest": parsed.guest,
                    "title": parsed.title,
                    "source": parsed.source,
                    "chunk_index": chunk_idx,
                },
            )
        )

    return chunks
