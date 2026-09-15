"""Web Fetch Tool with SSRF security protection and clean text extraction."""

import time
import socket
import ipaddress
import urllib.parse
import re
import requests
from typing import Dict, Any, Optional

from app.tools.base import Tool, ToolResult

# Blocked IP networks for SSRF defense
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud metadata
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("::1/128"),           # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-local
]

SCRIPT_STYLE_REGEX = re.compile(r'<(script|style|nav|footer|header)\b[^<]*(?:(?!<\/\1>)<[^<]*)*<\/\1>', re.IGNORECASE)
HTML_TAG_REGEX = re.compile(r'<[^>]+>')
WHITESPACE_REGEX = re.compile(r'\s+')


def validate_url_security(url: str) -> bool:
    """Ensure URL does not target localhost, private subnets, or metadata services."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "metadata.google.internal"):
        return False

    try:
        # Resolve hostname to check IP addresses
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_str = entry[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            for net in BLOCKED_NETWORKS:
                if ip_obj in net:
                    return False
        return True
    except Exception:
        return False


class WebFetchTool(Tool):
    name = "web_fetch"
    description = (
        "Fetch and extract clean readable text content from a public webpage URL. "
        "Protected by SSRF security defenses against private network access."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The HTTP or HTTPS webpage URL to read.",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum number of characters to extract (1000 - 20000).",
                "default": 6000,
            }
        },
        "required": ["url"],
    }
    timeout_seconds = 15.0

    async def execute(self, url: str, max_chars: int = 6000, **kwargs) -> ToolResult:
        t0 = time.perf_counter()

        if not validate_url_security(url):
            return ToolResult(
                tool_name=self.name,
                status="rejected",
                input_params={"url": url},
                output="",
                error_message="Access denied: URL targets a prohibited or private IP address (SSRF Defense).",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            res = requests.get(url, headers=headers, timeout=12.0)
            if res.status_code != 200:
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    input_params={"url": url},
                    output="",
                    error_message=f"HTTP fetch failed with status {res.status_code}",
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )

            raw_html = res.text
            # Extract page title
            title_match = re.search(r'<title>(.*?)</title>', raw_html, re.IGNORECASE)
            page_title = title_match.group(1).strip() if title_match else url

            # Strip scripts, styles, navigation, and tags
            no_scripts = SCRIPT_STYLE_REGEX.sub(' ', raw_html)
            clean_text = HTML_TAG_REGEX.sub(' ', no_scripts)
            normalized = WHITESPACE_REGEX.sub(' ', clean_text).strip()

            extracted = normalized[:max_chars]
            duration_ms = (time.perf_counter() - t0) * 1000

            return ToolResult(
                tool_name=self.name,
                status="success",
                input_params={"url": url, "max_chars": max_chars},
                output=extracted,
                metadata={
                    "page_title": page_title,
                    "url": url,
                    "char_count": len(extracted),
                    "total_page_chars": len(normalized),
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status="error",
                input_params={"url": url},
                output="",
                error_message=f"Web fetch error: {str(e)}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
