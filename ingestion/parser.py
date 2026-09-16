"""Markdown transcript parser and metadata extractor."""

import re
import os
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class ParsedTranscript:
    title: str
    guest: str
    source: str
    content: str
    content_hash: str
    file_path: str
    dialogue_turns: List[Dict[str, str]]

def parse_transcript_file(file_path: str) -> ParsedTranscript:
    """Read and extract structured metadata and dialogue turns from a transcript markdown file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Transcript file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    # Extract metadata headers (Supports both # Header and ChatPRD YAML frontmatter):
    yaml_guest = re.search(r"^guest:\s*(.+)$", raw_text, re.MULTILINE)
    yaml_title = re.search(r"^title:\s*(.+)$", raw_text, re.MULTILINE)

    guest_match = re.search(r"^#\s*Guest:\s*(.+)$", raw_text, re.MULTILINE)
    episode_match = re.search(r"^#\s*Episode:\s*(.+)$", raw_text, re.MULTILINE)
    source_match = re.search(r"^#\s*Source:\s*(.+)$", raw_text, re.MULTILINE)

    guest = guest_match.group(1).strip() if guest_match else (yaml_guest.group(1).strip() if yaml_guest else "Lenny's Guest")
    title = episode_match.group(1).strip() if episode_match else (yaml_title.group(1).strip() if yaml_title else os.path.splitext(os.path.basename(file_path))[0])
    source = source_match.group(1).strip() if source_match else ("Lenny's Podcast (ChatPRD)" if (yaml_guest or yaml_title) else "Lenny's Podcast")

    # Clean body text: remove YAML frontmatter and header lines
    body_text = re.sub(r"^---[\s\S]*?---\s*", "", raw_text)
    body_text = re.sub(r"^#\s*(Guest|Episode|Source):.*$", "", body_text, flags=re.MULTILINE).strip()

    # Parse dialogue turns: lines starting with **Speaker Name:**
    turn_pattern = re.compile(r"\*\*([^*:]+):\*\*\s*")
    turns = []
    
    parts = turn_pattern.split(body_text)
    # If the text starts with a speaker, parts[0] is empty, parts[1] is speaker, parts[2] is text, etc.
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            speaker = parts[i].strip()
            speech = parts[i+1].strip() if i + 1 < len(parts) else ""
            if speech:
                turns.append({"speaker": speaker, "text": speech})
    else:
        # Fallback if no dialogue markers found
        turns.append({"speaker": guest, "text": body_text})

    return ParsedTranscript(
        title=title,
        guest=guest,
        source=source,
        content=body_text,
        content_hash=content_hash,
        file_path=file_path,
        dialogue_turns=turns,
    )
