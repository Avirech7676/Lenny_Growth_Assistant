"""Live web search provider utilizing DuckDuckGo endpoints with resilient HTML/Lite parsing."""

import re
import urllib.parse
import logging
from html import unescape
from typing import List, Optional
import httpx

from app.services.search.base import (
    SearchProvider,
    DiscoveredSource,
    SourceCategory,
    FreshnessRequirement,
)

logger = logging.getLogger(__name__)

# Domain heuristic mapping to canonical source categories
DOMAIN_CATEGORY_MAP = {
    # Official / Primary / Standards
    "react.dev": SourceCategory.OFFICIAL,
    "python.org": SourceCategory.OFFICIAL,
    "fastapi.tiangolo.com": SourceCategory.OFFICIAL,
    "openai.com": SourceCategory.OFFICIAL,
    "anthropic.com": SourceCategory.OFFICIAL,
    "google.com": SourceCategory.OFFICIAL,
    "apple.com": SourceCategory.OFFICIAL,
    "microsoft.com": SourceCategory.OFFICIAL,
    "w3.org": SourceCategory.OFFICIAL,
    "developer.mozilla.org": SourceCategory.OFFICIAL,
    "ecma-international.org": SourceCategory.OFFICIAL,
    "iso.org": SourceCategory.OFFICIAL,

    # Academic / Scientific
    "arxiv.org": SourceCategory.ACADEMIC,
    "link.springer.com": SourceCategory.ACADEMIC,
    "nature.com": SourceCategory.ACADEMIC,
    "science.org": SourceCategory.ACADEMIC,
    "pubmed.ncbi.nlm.nih.gov": SourceCategory.ACADEMIC,
    "semanticscholar.org": SourceCategory.ACADEMIC,
    "ieee.org": SourceCategory.ACADEMIC,
    "acm.org": SourceCategory.ACADEMIC,
    "mit.edu": SourceCategory.ACADEMIC,
    "stanford.edu": SourceCategory.ACADEMIC,

    # News / Current Events / Sports
    "formula1.com": SourceCategory.OFFICIAL,
    "fifa.com": SourceCategory.OFFICIAL,
    "bbc.com": SourceCategory.NEWS,
    "reuters.com": SourceCategory.NEWS,
    "apnews.com": SourceCategory.NEWS,
    "bloomberg.com": SourceCategory.NEWS,
    "thehindu.com": SourceCategory.NEWS,
    "sportingnews.com": SourceCategory.NEWS,
    "espn.com": SourceCategory.NEWS,
    "espncricinfo.com": SourceCategory.NEWS,
    "theverge.com": SourceCategory.NEWS,
    "techcrunch.com": SourceCategory.NEWS,
    "arstechnica.com": SourceCategory.NEWS,

    # Industry / Professional / Venture
    "openview.com": SourceCategory.INDUSTRY,
    "openviewpartners.com": SourceCategory.INDUSTRY,
    "bessemer.com": SourceCategory.INDUSTRY,
    "bvp.com": SourceCategory.INDUSTRY,
    "a16z.com": SourceCategory.INDUSTRY,
    "sequoiacap.com": SourceCategory.INDUSTRY,
    "gartner.com": SourceCategory.INDUSTRY,
    "mckinsey.com": SourceCategory.INDUSTRY,
    "reforge.com": SourceCategory.INDUSTRY,

    # Technical / Code / Registry
    "npmjs.com": SourceCategory.TECHNICAL,
    "pypi.org": SourceCategory.TECHNICAL,
    "crates.io": SourceCategory.TECHNICAL,
    "github.com": SourceCategory.TECHNICAL,
    "gitlab.com": SourceCategory.TECHNICAL,
    "docker.com": SourceCategory.TECHNICAL,
    "kubernetes.io": SourceCategory.TECHNICAL,

    # Community / Practitioner
    "reddit.com": SourceCategory.COMMUNITY,
    "stackoverflow.com": SourceCategory.COMMUNITY,
    "news.ycombinator.com": SourceCategory.COMMUNITY,
    "dev.to": SourceCategory.COMMUNITY,
    "discord.com": SourceCategory.COMMUNITY,

    # Reference
    "wikipedia.org": SourceCategory.REFERENCE,
    "en.wikipedia.org": SourceCategory.REFERENCE,
    "britannica.com": SourceCategory.REFERENCE,

    # Financial / Market
    "sec.gov": SourceCategory.FINANCIAL,
    "rbi.org.in": SourceCategory.FINANCIAL,
    "investing.com": SourceCategory.FINANCIAL,
    "marketwatch.com": SourceCategory.FINANCIAL,
    "ft.com": SourceCategory.FINANCIAL,

    # Government / Public Data
    "gov.in": SourceCategory.GOVERNMENT,
    "data.gov": SourceCategory.GOVERNMENT,
    "whitehouse.gov": SourceCategory.GOVERNMENT,
    "who.int": SourceCategory.GOVERNMENT,

    # Product / Reviews
    "rtings.com": SourceCategory.PRODUCT,
    "notebookcheck.net": SourceCategory.PRODUCT,
    "wirecutter.com": SourceCategory.PRODUCT,
    "tomshardware.com": SourceCategory.PRODUCT,
}

def infer_source_category(domain: str, title: str = "", url: str = "") -> SourceCategory:
    """Classify a discovered source into one of the 11 categories."""
    d_clean = domain.lower().replace("www.", "")
    for known_domain, cat in DOMAIN_CATEGORY_MAP.items():
        if known_domain in d_clean:
            return cat

    if d_clean.endswith(".gov") or d_clean.endswith(".gov.in") or ".nic.in" in d_clean:
        return SourceCategory.GOVERNMENT
    if d_clean.endswith(".edu") or d_clean.endswith(".ac.uk") or d_clean.endswith(".edu.in"):
        return SourceCategory.ACADEMIC
    if any(k in d_clean for k in ["news", "times", "tribune", "post", "herald", "daily"]):
        return SourceCategory.NEWS
    if any(k in d_clean for k in ["forum", "community", "discuss"]):
        return SourceCategory.COMMUNITY
    if any(k in d_clean for k in ["docs.", "documentation.", "developer."]):
        return SourceCategory.OFFICIAL
    if any(k in d_clean for k in ["review", "benchmarks", "spec"]):
        return SourceCategory.PRODUCT

    # Title-based heuristics
    t_lower = title.lower()
    if any(w in t_lower for w in ["official documentation", "developer guide", "api reference"]):
        return SourceCategory.OFFICIAL
    if any(w in t_lower for w in ["paper", "journal", "proceedings", "study", "doi:"]):
        return SourceCategory.ACADEMIC

    return SourceCategory.INDUSTRY

def calculate_initial_authority(category: SourceCategory, domain: str) -> float:
    """Calculate authority weight based on source category and domain prestige."""
    base_scores = {
        SourceCategory.OFFICIAL: 0.98,
        SourceCategory.ACADEMIC: 0.96,
        SourceCategory.GOVERNMENT: 0.97,
        SourceCategory.FINANCIAL: 0.93,
        SourceCategory.INDUSTRY: 0.90,
        SourceCategory.TECHNICAL: 0.91,
        SourceCategory.NEWS: 0.88,
        SourceCategory.PRODUCT: 0.85,
        SourceCategory.REFERENCE: 0.84,
        SourceCategory.COMMUNITY: 0.78,
        SourceCategory.USER_PROVIDED: 0.99,
    }
    return base_scores.get(category, 0.82)


class DuckDuckGoProvider(SearchProvider):
    """Zero-credential live web search engine utilizing DuckDuckGo Lite."""

    def __init__(self, timeout: float = 2.5):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def get_provider_name(self) -> str:
        return "duckduckgo_live"

    def _parse_lite_html(self, html_text: str, max_results: int) -> List[DiscoveredSource]:
        links = re.findall(r"<a[^>]*href=['\"]([^'\"]+)['\"][^>]*class=['\"]result-link['\"][^>]*>(.*?)</a>", html_text, re.DOTALL)
        snippets = re.findall(r"<td[^>]*class=['\"]result-snippet['\"][^>]*>(.*?)</td>", html_text, re.DOTALL)

        results: List[DiscoveredSource] = []
        for i in range(min(len(links), max_results)):
            raw_url = links[i][0]
            if "uddg=" in raw_url:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                clean_url = parsed.get("uddg", [raw_url])[0]
            else:
                clean_url = raw_url

            raw_title = re.sub(r"<[^>]+>", "", links[i][1])
            title = unescape(raw_title).strip()
            
            snippet = ""
            if i < len(snippets):
                raw_snippet = re.sub(r"<[^>]+>", "", snippets[i])
                snippet = unescape(raw_snippet).strip()

            domain = urllib.parse.urlparse(clean_url).netloc.replace("www.", "")
            category = infer_source_category(domain, title, clean_url)
            authority = calculate_initial_authority(category, domain)
            is_primary = category in [SourceCategory.OFFICIAL, SourceCategory.GOVERNMENT, SourceCategory.ACADEMIC]

            why_useful = f"Authoritative {category.value} source on {domain}."
            if is_primary:
                why_useful = f"Primary source from {domain} providing direct first-party evidence."

            results.append(
                DiscoveredSource(
                    title=title,
                    url=clean_url,
                    domain=domain,
                    snippet=snippet,
                    category=category,
                    authority_score=authority,
                    freshness=FreshnessRequirement.CURRENT,
                    is_primary=is_primary,
                    why_useful=why_useful,
                )
            )

        return results

    def _parse_html_results(self, html_text: str, max_results: int) -> List[DiscoveredSource]:
        """Parse real search results from html.duckduckgo.com."""
        title_links = re.findall(r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html_text, re.DOTALL)
        snippet_links = re.findall(r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html_text, re.DOTALL)

        if not title_links:
            return self._parse_lite_html(html_text, max_results)

        results: List[DiscoveredSource] = []
        for i in range(min(len(title_links), max_results)):
            raw_url = title_links[i][0]
            if "uddg=" in raw_url:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                clean_url = parsed.get("uddg", [raw_url])[0]
            else:
                clean_url = raw_url

            raw_title = re.sub(r"<[^>]+>", "", title_links[i][1])
            title = unescape(raw_title).strip()

            snippet = ""
            if i < len(snippet_links):
                raw_snippet = re.sub(r"<[^>]+>", "", snippet_links[i][1])
                snippet = unescape(raw_snippet).strip()

            domain = urllib.parse.urlparse(clean_url).netloc.replace("www.", "")
            if not domain or not clean_url.startswith("http"):
                continue

            category = infer_source_category(domain, title, clean_url)
            authority = calculate_initial_authority(category, domain)
            is_primary = category in [SourceCategory.OFFICIAL, SourceCategory.GOVERNMENT, SourceCategory.ACADEMIC]

            why_useful = f"Authoritative {category.value} source on {domain}."
            if is_primary:
                why_useful = f"Primary source from {domain} providing direct first-party evidence."

            results.append(
                DiscoveredSource(
                    title=title,
                    url=clean_url,
                    domain=domain,
                    snippet=snippet,
                    category=category,
                    authority_score=authority,
                    freshness=FreshnessRequirement.CURRENT,
                    is_primary=is_primary,
                    why_useful=why_useful,
                )
            )

        return results

    def search(self, query: str, max_results: int = 5) -> List[DiscoveredSource]:
        """Synchronous live search with zero synthetic source fabrication."""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                # 1. Primary: HTML search
                res = client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query},
                    headers=self.headers,
                )
                if res.status_code in [200, 202] and len(res.text) > 500:
                    parsed = self._parse_html_results(res.text, max_results)
                    if parsed:
                        return parsed

                # 2. Secondary: Lite search
                res_lite = client.post(
                    "https://lite.duckduckgo.com/lite/",
                    data={"q": query},
                    headers=self.headers,
                )
                if res_lite.status_code in [200, 202] and len(res_lite.text) > 500:
                    parsed_lite = self._parse_lite_html(res_lite.text, max_results)
                    if parsed_lite:
                        return parsed_lite
        except Exception as e:
            logger.info("DuckDuckGo sync search encountered error (%s) for '%s'", e, query)

        # Resilient fallback across verified live endpoints
        fallback_results = self._fallback_live_search(query, max_results)
        if fallback_results:
            return fallback_results

        return []

    async def search_async(self, query: str, max_results: int = 5) -> List[DiscoveredSource]:
        """Asynchronous live search with zero synthetic source fabrication."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                # 1. Primary: HTML search
                res = await client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query},
                    headers=self.headers,
                )
                if res.status_code in [200, 202] and len(res.text) > 500:
                    parsed = self._parse_html_results(res.text, max_results)
                    if parsed:
                        return parsed

                # 2. Secondary: Lite search
                res_lite = await client.post(
                    "https://lite.duckduckgo.com/lite/",
                    data={"q": query},
                    headers=self.headers,
                )
                if res_lite.status_code in [200, 202] and len(res_lite.text) > 500:
                    parsed_lite = self._parse_lite_html(res_lite.text, max_results)
                    if parsed_lite:
                        return parsed_lite
        except Exception as e:
            logger.info("DuckDuckGo async search encountered error (%s) for '%s'", e, query)

        fallback_results = await self._fallback_live_search_async(query, max_results)
        if fallback_results:
            return fallback_results

        return []

    def _fallback_live_search(self, query: str, max_results: int = 5) -> List[DiscoveredSource]:
        """Resilient fallback live search executing across official live APIs and encyclopedia endpoints."""
        results: List[DiscoveredSource] = []
        q_lower = query.lower()

        # 1. Live NPM Registry search for software packages if relevant
        if any(pkg in q_lower for pkg in ["react", "vue", "angular", "npm", "fastapi", "nextjs"]):
            try:
                pkg_query = "react" if "react" in q_lower else query.split()[0]
                with httpx.Client(timeout=3.0) as client:
                    r_npm = client.get("https://registry.npmjs.org/-/v1/search", params={"text": pkg_query, "size": 2})
                    if r_npm.status_code == 200:
                        objs = r_npm.json().get("objects", [])
                        for obj in objs:
                            pkg = obj.get("package", {})
                            results.append(
                                DiscoveredSource(
                                    title=f"NPM Package: {pkg.get('name')} (v{pkg.get('version')})",
                                    url=f"https://www.npmjs.com/package/{pkg.get('name')}",
                                    domain="npmjs.com",
                                    snippet=f"{pkg.get('description', '')}. Latest active version: v{pkg.get('version')}.",
                                    category=SourceCategory.OFFICIAL,
                                    authority_score=0.98,
                                    freshness=FreshnessRequirement.CURRENT,
                                    is_primary=True,
                                    why_useful=f"Official NPM registry package metadata for {pkg.get('name')}.",
                                )
                            )
            except Exception as e:
                logger.debug("NPM search fallback exception: %s", e)

        # 2. Wikipedia live fulltext search API
        try:
            with httpx.Client(timeout=3.0, headers={"User-Agent": "TheLennyGrowthAssistant/2.0 (growth-assistant@example.com)"}) as client:
                r_wiki = client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query,
                        "format": "json",
                        "utf8": "1",
                        "srlimit": str(max_results),
                    }
                )
                if r_wiki.status_code == 200:
                    items = r_wiki.json().get("query", {}).get("search", [])
                    for it in items:
                        t = it.get("title", "")
                        s = unescape(re.sub(r'<[^>]+>', '', it.get("snippet", ""))).strip()
                        url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(t.replace(' ', '_'))}"
                        cat = infer_source_category("en.wikipedia.org", t, url)
                        results.append(
                            DiscoveredSource(
                                title=t,
                                url=url,
                                domain="en.wikipedia.org",
                                snippet=s,
                                category=cat,
                                authority_score=calculate_initial_authority(cat, "en.wikipedia.org"),
                                freshness=FreshnessRequirement.CURRENT,
                                is_primary=False,
                                why_useful=f"Verified encyclopedia article on {t}.",
                            )
                        )
        except Exception as e:
            logger.debug("Wikipedia search fallback exception: %s", e)

        return results[:max_results]

    async def _fallback_live_search_async(self, query: str, max_results: int = 5) -> List[DiscoveredSource]:
        """Asynchronous resilient fallback live search."""
        results: List[DiscoveredSource] = []
        q_lower = query.lower()

        # 1. Live NPM Registry search for software packages if relevant
        if any(pkg in q_lower for pkg in ["react", "vue", "angular", "npm", "fastapi", "nextjs"]):
            try:
                pkg_query = "react" if "react" in q_lower else query.split()[0]
                async with httpx.AsyncClient(timeout=3.0) as client:
                    r_npm = await client.get("https://registry.npmjs.org/-/v1/search", params={"text": pkg_query, "size": 2})
                    if r_npm.status_code == 200:
                        objs = r_npm.json().get("objects", [])
                        for obj in objs:
                            pkg = obj.get("package", {})
                            results.append(
                                DiscoveredSource(
                                    title=f"NPM Package: {pkg.get('name')} (v{pkg.get('version')})",
                                    url=f"https://www.npmjs.com/package/{pkg.get('name')}",
                                    domain="npmjs.com",
                                    snippet=f"{pkg.get('description', '')}. Latest active version: v{pkg.get('version')}.",
                                    category=SourceCategory.OFFICIAL,
                                    authority_score=0.98,
                                    freshness=FreshnessRequirement.CURRENT,
                                    is_primary=True,
                                    why_useful=f"Official NPM registry package metadata for {pkg.get('name')}.",
                                )
                            )
            except Exception as e:
                logger.debug("NPM search fallback async exception: %s", e)

        # 2. Wikipedia live fulltext search API
        try:
            async with httpx.AsyncClient(timeout=3.0, headers={"User-Agent": "LennyGrowthAssistant/2.0 (assistant@example.com)"}) as client:
                r_wiki = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query,
                        "format": "json",
                        "utf8": "1",
                        "srlimit": str(max_results),
                    }
                )
                if r_wiki.status_code == 200:
                    items = r_wiki.json().get("query", {}).get("search", [])
                    for it in items:
                        t = it.get("title", "")
                        s = unescape(re.sub(r'<[^>]+>', '', it.get("snippet", ""))).strip()
                        url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(t.replace(' ', '_'))}"
                        cat = infer_source_category("en.wikipedia.org", t, url)
                        results.append(
                            DiscoveredSource(
                                title=t,
                                url=url,
                                domain="en.wikipedia.org",
                                snippet=s,
                                category=cat,
                                authority_score=calculate_initial_authority(cat, "en.wikipedia.org"),
                                freshness=FreshnessRequirement.CURRENT,
                                is_primary=False,
                                why_useful=f"Verified encyclopedia article on {t}.",
                            )
                        )
        except Exception as e:
            logger.debug("Wikipedia search fallback async exception: %s", e)

        return results[:max_results]
