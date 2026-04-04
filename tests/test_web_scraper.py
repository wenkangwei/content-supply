"""Tests for WebScraper."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from content_supply.services.web_scraper import WebScraper

# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

SAMPLE_HTML = """\
<!DOCTYPE html>
<html>
<head>
    <title>Test Article</title>
    <meta property="og:image" content="https://example.com/og-image.jpg"/>
</head>
<body>
    <article>
        <h1>Test Article</h1>
        <p>This is the article body with enough content to be considered
        a real article. Trafilatura should extract this text successfully.</p>
    </article>
</body>
</html>
"""

HTML_WITH_TWITTER_IMAGE = """\
<!DOCTYPE html>
<html>
<head>
    <meta name="twitter:image" content="https://example.com/twitter-img.png"/>
    <title>Twitter Card Page</title>
</head>
<body><p>Some content here.</p></body>
</html>
"""

HTML_NO_IMAGE = """\
<!DOCTYPE html>
<html>
<head><title>No Image Page</title></head>
<body><p>Just text, no images.</p></body>
</html>
"""

HTML_REVERSED_META = """\
<!DOCTYPE html>
<html>
<head>
    <meta content="https://example.com/reversed.jpg" property="og:image"/>
</head>
<body><p>Content.</p></body>
</html>
"""


# ---------------------------------------------------------------------------
# _extract_image tests
# ---------------------------------------------------------------------------


class TestExtractImage:
    def test_og_image(self):
        url = WebScraper._extract_image(SAMPLE_HTML)
        assert url == "https://example.com/og-image.jpg"

    def test_twitter_image(self):
        url = WebScraper._extract_image(HTML_WITH_TWITTER_IMAGE)
        assert url == "https://example.com/twitter-img.png"

    def test_no_image(self):
        url = WebScraper._extract_image(HTML_NO_IMAGE)
        assert url == ""

    def test_reversed_meta_order(self):
        url = WebScraper._extract_image(HTML_REVERSED_META)
        assert url == "https://example.com/reversed.jpg"


# ---------------------------------------------------------------------------
# _is_allowed_by_robots tests
# ---------------------------------------------------------------------------


class TestRobotsCheck:
    def test_default_allow_on_exception(self):
        """When robots.txt cannot be fetched, default to allow."""
        with patch("content_supply.services.web_scraper.robotparser.RobotFileParser") as MockRP:
            rp_instance = MockRP.return_value
            rp_instance.read.side_effect = Exception("network error")
            result = WebScraper._is_allowed_by_robots("https://example.com/page")
            assert result is True


# ---------------------------------------------------------------------------
# scrape integration tests (with mocked httpx)
# ---------------------------------------------------------------------------


@pytest.fixture
def scraper():
    return WebScraper(timeout=10)


def _make_response(html: str, status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response with the given HTML body."""
    return httpx.Response(
        status_code=status_code,
        request=httpx.Request("GET", "https://example.com/article"),
        text=html,
        headers={"content-type": "text/html"},
    )


class TestScrape:
    @pytest.mark.asyncio
    async def test_scrape_success(self, scraper):
        mock_response = _make_response(SAMPLE_HTML)

        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await scraper.scrape("https://example.com/article", source_name="test")

        assert result is not None
        assert result.url == "https://example.com/article"
        assert result.source_name == "test"
        assert result.image_url == "https://example.com/og-image.jpg"
        # Title should be extracted (trafilatura or <title>)
        assert result.title != ""

    @pytest.mark.asyncio
    async def test_scrape_http_error(self, scraper):
        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "404",
                request=httpx.Request("GET", "https://example.com/missing"),
                response=httpx.Response(404),
            ),
        ):
            result = await scraper.scrape("https://example.com/missing")

        assert result is None

    @pytest.mark.asyncio
    async def test_scrape_request_error(self, scraper):
        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("connection refused"),
        ):
            result = await scraper.scrape("https://unreachable.example.com/")

        assert result is None

    @pytest.mark.asyncio
    async def test_scrape_empty_page_returns_none(self, scraper):
        """When neither title nor content can be extracted, return None."""
        empty_html = "<html><head></head><body></body></html>"
        mock_response = _make_response(empty_html)

        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await scraper.scrape("https://example.com/empty")

        assert result is None

    @pytest.mark.asyncio
    async def test_scrape_robots_blocked(self, scraper):
        """When robots.txt blocks the URL, return None."""
        with patch.object(
            WebScraper,
            "_is_allowed_by_robots",
            return_value=False,
        ):
            result = await scraper.scrape("https://example.com/blocked")

        assert result is None
