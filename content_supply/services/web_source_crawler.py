"""Web source crawler — auto-discover and fetch articles from website list pages.

No CSS selectors needed. Just paste the list page URL and the crawler will
automatically find article links using heuristics (path depth, article-like
URL patterns, link text length, same-domain grouping).
"""

import asyncio
import logging
import re
from collections import Counter
from typing import Optional
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup

from content_supply.services.types import CrawledItem

logger = logging.getLogger(__name__)

# Common non-article path prefixes to skip
_SKIP_PATHS = {
    "", "/", "/index", "/home",
    "/about", "/contact", "/login", "/signup", "/register",
    "/search", "/tags", "/tag", "/category", "/categories",
    "/archive", "/privacy", "/terms", "/legal",
    "/feed", "/rss", "/atom", "/sitemap",
    "/api", "/static", "/assets", "/images", "/css", "/js",
    "/robots.txt", "/favicon.ico",
}

# Article-like URL patterns (one of these matching → likely an article)
_ARTICLE_PATTERNS = [
    re.compile(r"/\d{4}/\d{2}/"),                # /2026/04/ date path
    re.compile(r"/p/\d+"),                        # /p/123456
    re.compile(r"/(article|post|blog|news|story|detail)/", re.I),
    re.compile(r"/(a|p|n)/[\w-]{4,}"),            # /a/slug-here
    re.compile(r"/\d{6,}"),                       # /123456789 (numeric ID)
    re.compile(r"-\d+\.html?$"),                   # title-12345.html
    re.compile(r"/\d{4}/\d{2}/\d{2}/"),           # /2026/04/11/ full date
]

# Navigation / boilerplate link text patterns to skip
_SKIP_TEXT = re.compile(
    r"^(首页|主页|登录|注册|关于|联系|搜索|更多|订阅|评论|分享|下载|app)"
    r"|(home|login|sign|about|contact|search|more|subscribe|comment|share|download)",
    re.I,
)

# Paths that look like tag/category pages (not articles)
_TAG_PATH_RE = re.compile(
    r"^/(t|tag|tags|topic|topics|c|category|categories|channel|channels)/[^/]+/?$",
    re.I,
)


class WebSourceCrawler:
    """Auto-discover and crawl articles from a website list page."""

    def __init__(self, timeout: int = 30, max_concurrent: int = 3):
        self.timeout = timeout
        self.max_concurrent = max_concurrent

    async def discover_article_urls(
        self,
        list_url: str,
        max_articles: int = 10,
    ) -> list[str]:
        """Fetch a list page and auto-discover article URLs using heuristics.

        No CSS selector required. Scoring is based on:
        - URL path depth (deeper = more likely an article)
        - Article-like URL patterns (/article/, /2026/04/, numeric IDs, etc.)
        - Link text length (longer titles = more likely articles)
        - Same-domain grouping (keep links on the same site)
        - Path pattern frequency (the most common path structure = article list)
        """
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                },
            ) as client:
                response = await client.get(list_url)
                response.raise_for_status()
                html = response.text

            parsed_page = urlparse(list_url)
            page_domain = parsed_page.netloc

            soup = BeautifulSoup(html, "html.parser")

            # Remove nav/header/footer/script/style to reduce noise
            for tag in soup.find_all(["nav", "header", "footer", "script", "style", "aside"]):
                tag.decompose()

            # Collect all <a> tags with scoring
            candidates: list[tuple[str, float, str]] = []  # (url, score, text)

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                text = a_tag.get_text(strip=True)

                # Resolve relative URLs
                full_url = urljoin(list_url, href)
                parsed = urlparse(full_url)

                # Must be http(s) and on same domain (or subdomain)
                if parsed.scheme not in ("http", "https"):
                    continue
                if parsed.netloc != page_domain and not parsed.netloc.endswith("." + page_domain):
                    continue

                path = parsed.path.rstrip("/")

                # Skip known non-article paths
                if path.lower() in _SKIP_PATHS:
                    continue
                if path.count("/") < 1:
                    continue

                # Skip boilerplate link text
                if not text or (len(text) < 4 and not any(c.isdigit() for c in text)):
                    continue
                if _SKIP_TEXT.match(text):
                    continue

                # --- Scoring ---
                score = 0.0

                # 1. Path depth (more segments → more likely article)
                segments = [s for s in path.split("/") if s]
                score += min(len(segments), 5) * 1.0

                # 2. Article-like URL patterns
                for pattern in _ARTICLE_PATTERNS:
                    if pattern.search(path):
                        score += 5.0
                        break

                # 3. Link text length (article titles are usually 15+ chars)
                text_len = len(text)
                if text_len >= 15:
                    score += 5.0
                elif text_len >= 8:
                    score += 3.0
                elif text_len >= 4:
                    score += 1.0

                # 4. Penalize tag/category pages
                if _TAG_PATH_RE.match(path):
                    score -= 5.0

                # 4. Has slug-like segment (contains hyphens or Chinese)
                slug_like = any("-" in s or any("\u4e00" <= c <= "\u9fff" for c in s) for s in segments)
                if slug_like:
                    score += 2.0

                # 5. URL has query params (often pagination/filter, slightly penalize)
                if parsed.query and "page" not in parsed.query.lower():
                    score -= 0.5

                # 6. Penalize very short paths like /xxx (single segment)
                if len(segments) == 1 and len(segments[0]) < 10:
                    score -= 2.0

                candidates.append((full_url, score, text))

            if not candidates:
                logger.info("No candidate links found on %s", list_url)
                return []

            # --- Frequency boost: find the most common path pattern ---
            # Group by path template (e.g., "/article/xxx" → "/article/*")
            path_templates: list[str] = []
            for url, _, _ in candidates:
                parts = urlparse(url).path.split("/")
                # Replace the last segment with "*" to create a pattern
                if len(parts) >= 3:
                    template = "/".join(parts[:-1]) + "/*"
                else:
                    template = urlparse(url).path
                path_templates.append(template)

            counter = Counter(path_templates)
            if counter:
                top_template, top_count = counter.most_common(1)[0]
                # Boost links that share the most common pattern (they're the article list)
                for i, (url, score, text) in enumerate(candidates):
                    if path_templates[i] == top_template:
                        candidates[i] = (url, score + 3.0, text)

            # Deduplicate, sort by score descending
            seen: set[str] = set()
            scored: list[tuple[str, float]] = []
            for url, score, text in candidates:
                if url not in seen:
                    seen.add(url)
                    scored.append((url, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            urls = [u for u, _ in scored[:max_articles]]

            logger.info(
                "Auto-discovered %d article URLs from %s (top scores: %.1f, %.1f, %.1f)",
                len(urls),
                list_url,
                scored[0][1] if scored else 0,
                scored[1][1] if len(scored) > 1 else 0,
                scored[2][1] if len(scored) > 2 else 0,
            )
            return urls

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "HTTP error fetching list page %s: %s",
                list_url, exc.response.status_code,
            )
            return []
        except Exception:
            logger.error("Error discovering URLs from %s", list_url, exc_info=True)
            return []

    async def crawl_source(
        self,
        source_config: dict,
    ) -> list[CrawledItem]:
        """Discover and scrape articles from a configured web source.

        Config fields used:
            url           — list page URL (required)
            name          — source name for tagging
            max_articles  — max articles per run (default 10)
            category      — content category tag
        """
        from content_supply.services.web_scraper import WebScraper

        list_url = source_config["url"]
        max_articles = source_config.get("max_articles", 10)
        source_name = source_config.get("name", "")
        category = source_config.get("category", "")

        # Step 1: auto-discover article URLs
        urls = await self.discover_article_urls(
            list_url=list_url,
            max_articles=max_articles,
        )
        if not urls:
            logger.info("No URLs discovered for source '%s'", source_name)
            return []

        # Step 2: scrape each URL concurrently
        scraper = WebScraper()
        items: list[CrawledItem] = []
        sem = asyncio.Semaphore(self.max_concurrent)

        async def _scrape_one(url: str) -> Optional[CrawledItem]:
            async with sem:
                try:
                    item = await scraper.scrape(url, source_name=source_name)
                    if item:
                        item.source_type = "web"
                        item.extra["category"] = category
                    return item
                except Exception as e:
                    logger.warning("Failed to scrape %s: %s", url, e)
                    return None

        results = await asyncio.gather(
            *[_scrape_one(u) for u in urls], return_exceptions=True
        )

        for result in results:
            if isinstance(result, CrawledItem):
                items.append(result)

        logger.info(
            "WebSource '%s': discovered %d URLs, scraped %d articles",
            source_name, len(urls), len(items),
        )
        return items
