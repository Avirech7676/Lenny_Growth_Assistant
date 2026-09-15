"""Unified multi-format file and image parser for File Intelligence.

Supports:
- PDF (.pdf)
- Word (.docx, .doc)
- Spreadsheets (.xlsx, .xls)
- Tabular data (.csv)
- Data serialization (.json, .jsonl)
- Text documents (.txt)
- Markdown (.md, .markdown)
- Source code (.py, .js, .ts, .tsx, .jsx, .java, .cpp, .c, .h, .cs, .go, .rs, .rb, .php, .swift, .kt, .sh, .sql)
- Images (.png, .jpg, .jpeg, .webp, .gif, .bmp, .svg)
"""

import io
import os
import csv
import json
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.services.file_intelligence.models import FileType, ParsedFile

logger = logging.getLogger(__name__)

MAX_EXTRACT_CHARS = 24_000
MAX_ROWS_TABULAR = 300
MAX_SHEETS = 5


class UnifiedFileParser:
    """Multi-format parser with fail-safe degradation and image support."""

    _EXTENSION_MAP = {
        # PDF
        ".pdf": (FileType.PDF, "_parse_pdf"),
        # Word
        ".docx": (FileType.DOCX, "_parse_docx"),
        ".doc": (FileType.DOCX, "_parse_docx"),
        # Excel
        ".xlsx": (FileType.XLSX, "_parse_xlsx"),
        ".xls": (FileType.XLSX, "_parse_xlsx"),
        # Tabular
        ".csv": (FileType.CSV, "_parse_csv"),
        # JSON
        ".json": (FileType.JSON, "_parse_json"),
        ".jsonl": (FileType.JSON, "_parse_json"),
        # Plain text & markdown
        ".txt": (FileType.TXT, "_parse_text"),
        ".text": (FileType.TXT, "_parse_text"),
        ".md": (FileType.MARKDOWN, "_parse_markdown"),
        ".markdown": (FileType.MARKDOWN, "_parse_markdown"),
        # Source code
        ".py": (FileType.CODE, "_parse_code"),
        ".js": (FileType.CODE, "_parse_code"),
        ".ts": (FileType.CODE, "_parse_code"),
        ".jsx": (FileType.CODE, "_parse_code"),
        ".tsx": (FileType.CODE, "_parse_code"),
        ".java": (FileType.CODE, "_parse_code"),
        ".go": (FileType.CODE, "_parse_code"),
        ".rs": (FileType.CODE, "_parse_code"),
        ".cpp": (FileType.CODE, "_parse_code"),
        ".c": (FileType.CODE, "_parse_code"),
        ".h": (FileType.CODE, "_parse_code"),
        ".cs": (FileType.CODE, "_parse_code"),
        ".swift": (FileType.CODE, "_parse_code"),
        ".kt": (FileType.CODE, "_parse_code"),
        ".rb": (FileType.CODE, "_parse_code"),
        ".php": (FileType.CODE, "_parse_code"),
        ".sh": (FileType.CODE, "_parse_code"),
        ".bash": (FileType.CODE, "_parse_code"),
        ".sql": (FileType.CODE, "_parse_code"),
        # Images
        ".png": (FileType.IMAGE, "_parse_image"),
        ".jpg": (FileType.IMAGE, "_parse_image"),
        ".jpeg": (FileType.IMAGE, "_parse_image"),
        ".webp": (FileType.IMAGE, "_parse_image"),
        ".gif": (FileType.IMAGE, "_parse_image"),
        ".bmp": (FileType.IMAGE, "_parse_image"),
        ".svg": (FileType.IMAGE, "_parse_svg"),
    }

    def parse_bytes(self, filename: str, data: bytes) -> ParsedFile:
        """Parse raw file bytes dispatching by extension with fallback."""
        ext = Path(filename).suffix.lower()
        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or "application/octet-stream"

        if ext in self._EXTENSION_MAP:
            ftype, method_name = self._EXTENSION_MAP[ext]
            try:
                return getattr(self, method_name)(filename, data, mime_type, ftype)
            except Exception as exc:
                logger.warning("Parser %s failed for %s: %s", method_name, filename, exc)
                return ParsedFile(
                    filename=filename,
                    file_type=ftype,
                    mime_type=mime_type,
                    content=self._try_text_fallback(data),
                    error=f"Primary parser error ({type(exc).__name__}): {exc}",
                )

        # Fallback text
        return ParsedFile(
            filename=filename,
            file_type=FileType.UNKNOWN,
            mime_type=mime_type,
            content=self._try_text_fallback(data),
            error="Generic text extraction used for unindexed file extension.",
        )

    def parse_file(self, filepath: str) -> ParsedFile:
        """Parse from local disk path."""
        p = Path(filepath)
        if not p.exists():
            return ParsedFile(
                filename=p.name,
                file_type=FileType.UNKNOWN,
                mime_type="application/octet-stream",
                content="",
                error=f"File not found: {filepath}",
            )
        try:
            return self.parse_bytes(p.name, p.read_bytes())
        except Exception as exc:
            return ParsedFile(
                filename=p.name,
                file_type=FileType.UNKNOWN,
                mime_type="application/octet-stream",
                content="",
                error=f"Read error: {exc}",
            )

    # --------------------------------------------------------------------------
    # Document Parsers
    # --------------------------------------------------------------------------

    def _parse_pdf(self, filename: str, data: bytes, mime_type: str, ftype: FileType) -> ParsedFile:
        try:
            import pypdf
        except ImportError:
            return ParsedFile(
                filename=filename,
                file_type=ftype,
                mime_type=mime_type,
                content=self._try_text_fallback(data),
                error="pypdf library not available.",
            )

        reader = pypdf.PdfReader(io.BytesIO(data))
        pages_text: List[str] = []
        for i, page in enumerate(reader.pages):
            txt = (page.extract_text() or "").strip()
            if txt:
                pages_text.append(f"--- Page {i + 1} ---\n{txt}")
            if sum(len(p) for p in pages_text) > MAX_EXTRACT_CHARS:
                break

        content = "\n\n".join(pages_text) if pages_text else "[Empty PDF or Scanned Document]"
        metadata = {}
        if reader.metadata:
            for k in ["Title", "Author", "Subject", "Creator"]:
                v = getattr(reader.metadata, k.lower(), None) or reader.metadata.get(f"/{k}")
                if v:
                    metadata[k] = str(v)[:120]

        return ParsedFile(
            filename=filename,
            file_type=ftype,
            mime_type=mime_type or "application/pdf",
            content=content[:MAX_EXTRACT_CHARS],
            page_or_row_count=len(reader.pages),
            metadata=metadata,
            truncated=len(content) > MAX_EXTRACT_CHARS,
        )

    def _parse_docx(self, filename: str, data: bytes, mime_type: str, ftype: FileType) -> ParsedFile:
        try:
            import docx
        except ImportError:
            return ParsedFile(
                filename=filename,
                file_type=ftype,
                mime_type=mime_type,
                content=self._try_text_fallback(data),
                error="python-docx library not available.",
            )

        doc = docx.Document(io.BytesIO(data))
        elements: List[str] = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                if p.style and p.style.name and p.style.name.startswith("Heading"):
                    elements.append(f"## {text}")
                else:
                    elements.append(text)

        # Also extract table text
        for table in doc.tables:
            for row in table.rows:
                row_vals = [cell.text.strip() for cell in row.cells]
                if any(row_vals):
                    elements.append(" | ".join(row_vals))

        content = "\n\n".join(elements)
        metadata = {}
        if doc.core_properties:
            if doc.core_properties.title:
                metadata["title"] = doc.core_properties.title[:100]
            if doc.core_properties.author:
                metadata["author"] = doc.core_properties.author[:100]

        return ParsedFile(
            filename=filename,
            file_type=ftype,
            mime_type=mime_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=content[:MAX_EXTRACT_CHARS],
            page_or_row_count=len(doc.paragraphs),
            metadata=metadata,
            truncated=len(content) > MAX_EXTRACT_CHARS,
        )

    def _parse_xlsx(self, filename: str, data: bytes, mime_type: str, ftype: FileType) -> ParsedFile:
        try:
            import openpyxl
        except ImportError:
            return ParsedFile(
                filename=filename,
                file_type=ftype,
                mime_type=mime_type,
                content=self._try_text_fallback(data),
                error="openpyxl library not available.",
            )

        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        sheets_out: List[str] = []
        total_rows = 0

        for sheet_name in list(wb.sheetnames)[:MAX_SHEETS]:
            ws = wb[sheet_name]
            sheet_rows = []
            for r_idx, row in enumerate(ws.iter_rows(values_only=True, max_row=MAX_ROWS_TABULAR)):
                cells = [str(c) if c is not None else "" for c in row]
                if any(cells):
                    sheet_rows.append(" | ".join(cells))
            if sheet_rows:
                total_rows += len(sheet_rows)
                sheets_out.append(f"=== Sheet: {sheet_name} ({len(sheet_rows)} rows) ===\n" + "\n".join(sheet_rows))

        content = "\n\n".join(sheets_out)
        return ParsedFile(
            filename=filename,
            file_type=ftype,
            mime_type=mime_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content[:MAX_EXTRACT_CHARS],
            page_or_row_count=total_rows,
            metadata={"sheets": list(wb.sheetnames[:MAX_SHEETS]), "total_sheets": len(wb.sheetnames)},
            truncated=len(content) > MAX_EXTRACT_CHARS,
        )

    def _parse_csv(self, filename: str, data: bytes, mime_type: str, ftype: FileType) -> ParsedFile:
        text = data.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = []
        for i, row in enumerate(reader):
            if i >= MAX_ROWS_TABULAR:
                break
            rows.append(" | ".join(row))

        content = "\n".join(rows)
        header = rows[0] if rows else ""
        return ParsedFile(
            filename=filename,
            file_type=ftype,
            mime_type=mime_type or "text/csv",
            content=content[:MAX_EXTRACT_CHARS],
            page_or_row_count=len(rows),
            metadata={"row_count": len(rows), "columns_header": header[:120]},
            truncated=len(content) > MAX_EXTRACT_CHARS,
        )

    def _parse_json(self, filename: str, data: bytes, mime_type: str, ftype: FileType) -> ParsedFile:
        text = data.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
            pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
            keys = list(parsed.keys())[:10] if isinstance(parsed, dict) else [f"array[{len(parsed)}]"]
            return ParsedFile(
                filename=filename,
                file_type=ftype,
                mime_type=mime_type or "application/json",
                content=pretty[:MAX_EXTRACT_CHARS],
                page_or_row_count=len(parsed) if isinstance(parsed, (dict, list)) else 1,
                metadata={"top_level_keys": keys},
                truncated=len(pretty) > MAX_EXTRACT_CHARS,
            )
        except json.JSONDecodeError:
            # Check JSONL
            lines = text.splitlines()
            records = [line for line in lines[:MAX_ROWS_TABULAR] if line.strip()]
            return ParsedFile(
                filename=filename,
                file_type=ftype,
                mime_type="application/jsonl",
                content="\n".join(records)[:MAX_EXTRACT_CHARS],
                page_or_row_count=len(records),
                metadata={"jsonl_lines": len(records)},
                truncated=len(text) > MAX_EXTRACT_CHARS,
            )

    def _parse_text(self, filename: str, data: bytes, mime_type: str, ftype: FileType) -> ParsedFile:
        content = data.decode("utf-8", errors="replace")
        lines = content.splitlines()
        return ParsedFile(
            filename=filename,
            file_type=ftype,
            mime_type=mime_type or "text/plain",
            content=content[:MAX_EXTRACT_CHARS],
            page_or_row_count=len(lines),
            metadata={"line_count": len(lines)},
            truncated=len(content) > MAX_EXTRACT_CHARS,
        )

    def _parse_markdown(self, filename: str, data: bytes, mime_type: str, ftype: FileType) -> ParsedFile:
        content = data.decode("utf-8", errors="replace")
        headings = [line.strip("# ") for line in content.splitlines() if line.startswith("#")]
        return ParsedFile(
            filename=filename,
            file_type=ftype,
            mime_type=mime_type or "text/markdown",
            content=content[:MAX_EXTRACT_CHARS],
            page_or_row_count=len(content.splitlines()),
            metadata={"headings": headings[:8]},
            truncated=len(content) > MAX_EXTRACT_CHARS,
        )

    def _parse_code(self, filename: str, data: bytes, mime_type: str, ftype: FileType) -> ParsedFile:
        content = data.decode("utf-8", errors="replace")
        ext = Path(filename).suffix.lstrip(".")
        lang = {
            "py": "python", "js": "javascript", "ts": "typescript", "jsx": "jsx",
            "tsx": "tsx", "java": "java", "go": "go", "rs": "rust", "cpp": "c++",
            "c": "c", "h": "c", "cs": "csharp", "swift": "swift", "kt": "kotlin",
            "rb": "ruby", "php": "php", "sh": "bash", "bash": "bash", "sql": "sql",
        }.get(ext, ext)

        wrapped = f"```{lang}\n{content[:MAX_EXTRACT_CHARS]}\n```"
        return ParsedFile(
            filename=filename,
            file_type=ftype,
            mime_type=mime_type or "text/x-source",
            content=wrapped,
            page_or_row_count=len(content.splitlines()),
            metadata={"language": lang, "lines": len(content.splitlines())},
            truncated=len(content) > MAX_EXTRACT_CHARS,
        )

    def _parse_image(self, filename: str, data: bytes, mime_type: str, ftype: FileType) -> ParsedFile:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data))
            width, height = img.size
            format_name = img.format or "UNKNOWN"
            mode = img.mode

            # Extract EXIF if present
            exif_data = {}
            if hasattr(img, "_getexif") and img._getexif():
                raw_exif = img._getexif() or {}
                for tag_id, val in list(raw_exif.items())[:6]:
                    exif_data[str(tag_id)] = str(val)[:40]

            aspect_ratio = f"{round(width / max(height, 1), 2)}:1"
            content = (
                f"[IMAGE FILE SPECIFICATIONS]\n"
                f"Filename: {filename}\n"
                f"Format: {format_name}\n"
                f"Dimensions: {width} x {height} pixels\n"
                f"Aspect Ratio: {aspect_ratio}\n"
                f"Color Mode: {mode}\n"
                f"Byte Size: {len(data):,} bytes\n"
            )
            if exif_data:
                content += f"EXIF Metadata Tags: {exif_data}\n"

            return ParsedFile(
                filename=filename,
                file_type=ftype,
                mime_type=mime_type or f"image/{format_name.lower()}",
                content=content,
                page_or_row_count=1,
                metadata={
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": mode,
                    "aspect_ratio": aspect_ratio,
                },
            )
        except Exception as exc:
            return ParsedFile(
                filename=filename,
                file_type=ftype,
                mime_type=mime_type or "image/png",
                content=f"[Image binary data: {len(data)} bytes]",
                page_or_row_count=1,
                metadata={"size_bytes": len(data)},
                error=f"Image metadata extraction failed: {exc}",
            )

    def _parse_svg(self, filename: str, data: bytes, mime_type: str, ftype: FileType) -> ParsedFile:
        text = data.decode("utf-8", errors="replace")
        return ParsedFile(
            filename=filename,
            file_type=ftype,
            mime_type="image/svg+xml",
            content=text[:MAX_EXTRACT_CHARS],
            page_or_row_count=1,
            metadata={"format": "SVG", "is_vector": True},
            truncated=len(text) > MAX_EXTRACT_CHARS,
        )

    def _try_text_fallback(self, data: bytes) -> str:
        try:
            return data.decode("utf-8", errors="replace")[:MAX_EXTRACT_CHARS]
        except Exception:
            return "[Binary content: raw bytes could not be decoded]"


_UNIFIED_PARSER = UnifiedFileParser()


def get_unified_file_parser() -> UnifiedFileParser:
    """Access singleton parser."""
    return _UNIFIED_PARSER
