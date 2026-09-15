"""HTML sanitization utilities — shared by orchestrator and tools.

Extracted here to break the circular import cycle:
  orchestrator.py → tools/artifact_generator.py → orchestrator.py
"""

import re
import bleach
from bleach.css_sanitizer import CSSSanitizer

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

_css_sanitizer = CSSSanitizer()
_SCRIPT_BLOCK_REGEX = re.compile(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', re.IGNORECASE)
_STYLE_BLOCK_REGEX = re.compile(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', re.IGNORECASE)


def sanitize_artifact_content(raw_html: str) -> str:
    """Sanitize LLM-generated HTML artifact content using bleach whitelist and CSS sanitizer."""
    stripped = _SCRIPT_BLOCK_REGEX.sub('', raw_html)
    stripped = _STYLE_BLOCK_REGEX.sub('', stripped)
    return bleach.clean(
        stripped,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRS,
        css_sanitizer=_css_sanitizer,
        strip=True
    )
