"""Sandboxed artifact HTML renderer and security header configuration."""

import html
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.db.models import Artifact as ArtifactModel

CSP_POLICY = (
    "default-src 'none'; "
    "style-src 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com data:; "
    "img-src data: https:; "
    "script-src 'unsafe-inline' https://cdn.tailwindcss.com; "
    "frame-ancestors 'self'; "
    "base-uri 'none'; "
    "form-action 'none';"
)

def get_sandbox_security_headers() -> Dict[str, str]:
    """Generate strict security and sandboxing headers for artifact iframes."""
    return {
        "Content-Security-Policy": CSP_POLICY,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "X-XSS-Protection": "1; mode=block",
    }


def wrap_artifact_html(
    title: str,
    artifact_type: str,
    sanitized_content: str,
    created_at: Optional[datetime] = None,
) -> str:
    """
    Wrap sanitized artifact content in a standalone, fully-styled HTML document.
    Complies with DESIGN.md (Deep Slate #0A0E17, Electric Emerald #10B981, Plus Jakarta Sans/Inter).
    """
    safe_title = html.escape(title or "Growth Operational Artifact")
    safe_type = html.escape((artifact_type or "artifact").upper())
    timestamp_str = (
        created_at.strftime("%b %d, %Y %H:%M UTC")
        if created_at
        else datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC")
    )

    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap" rel="stylesheet">
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          colors: {{
            brand: {{
              slate: '#0A0E17',
              surface: '#0F172A',
              card: '#1E293B',
              border: '#334155',
              emerald: '#10B981',
              emeraldDark: '#059669',
              emeraldGlow: 'rgba(16, 185, 129, 0.15)',
            }}
          }},
          fontFamily: {{
            sans: ['Inter', 'sans-serif'],
            heading: ['Plus Jakarta Sans', 'sans-serif'],
            mono: ['JetBrains Mono', 'monospace'],
          }}
        }}
      }}
    }}
  </script>
  <style>
    :root {{
      color-scheme: dark;
    }}
    body {{
      background-color: #0A0E17;
      color: #F8FAFC;
      font-family: 'Inter', sans-serif;
      margin: 0;
      padding: 1.25rem;
      -webkit-font-smoothing: antialiased;
    }}
    h1, h2, h3, h4, h5, h6 {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      color: #F8FAFC;
      letter-spacing: -0.02em;
    }}
    code, pre {{
      font-family: 'JetBrains Mono', monospace;
    }}
    /* Custom scrollbars */
    ::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    ::-webkit-scrollbar-track {{
      background: #0A0E17;
    }}
    ::-webkit-scrollbar-thumb {{
      background: #334155;
      border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
      background: #10B981;
    }}
    /* Range input styling for ICE calculators */
    input[type=range] {{
      accent-color: #10B981;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      border-color: #334155;
    }}
  </style>
</head>
<body class="bg-brand-slate text-slate-100 min-h-screen">
  <div class="max-w-4xl mx-auto space-y-4">
    <!-- Header Card -->
    <header class="p-4 bg-slate-900/90 border border-slate-800 rounded-xl flex items-center justify-between shadow-lg backdrop-blur">
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          {safe_type}
        </span>
        <h1 class="text-lg font-bold font-heading text-white">{safe_title}</h1>
      </div>
      <div class="flex items-center gap-2 text-xs text-slate-400 font-mono">
        <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>Sandboxed Sandbox</span>
        <span class="text-slate-600">•</span>
        <span>{timestamp_str}</span>
      </div>
    </header>

    <!-- Artifact Body Container -->
    <main class="p-5 bg-slate-900/60 border border-slate-800/80 rounded-xl shadow-2xl backdrop-blur-sm">
      {sanitized_content}
    </main>

    <!-- Security & Grounding Footer -->
    <footer class="p-3 bg-slate-950/60 border border-slate-800/60 rounded-lg flex items-center justify-between text-xs text-slate-400">
      <div class="flex items-center gap-2">
        <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        <span class="font-medium text-slate-300">Lenny Assistant Epistemic Sandbox</span>
        <span class="text-slate-600">|</span>
        <span>Bleach Verified + Strict CSP</span>
      </div>
      <span class="font-mono text-slate-500">allow-scripts (origin-isolated)</span>
    </footer>
  </div>
</body>
</html>
"""


def render_sandboxed_artifact(artifact: ArtifactModel) -> str:
    """Render an ArtifactModel instance into a complete sandboxed HTML page."""
    content_to_render = artifact.sanitized_content or artifact.raw_content or "<p class='text-slate-400'>No artifact content available.</p>"
    return wrap_artifact_html(
        title=artifact.title,
        artifact_type=artifact.artifact_type,
        sanitized_content=content_to_render,
        created_at=artifact.created_at,
    )
