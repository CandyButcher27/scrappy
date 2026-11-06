import os

from markdownify import markdownify

from .check import Result
from .net import key, request, request_json


def scrapling_http(url: str) -> Result:
    from scrapling.fetchers import Fetcher

    page = Fetcher.get(url, impersonate="chrome")
    return Result(url, "scrapling_http", page.css("title::text").get(), page.markdown(), page.status)


def scrapling_browser(url: str) -> Result:
    from scrapling.fetchers import StealthyFetcher

    page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
    return Result(url, "scrapling_browser", page.css("title::text").get(), page.markdown(), page.status)


def firecrawl(url: str) -> Result:
    data = request_json(
        "https://api.firecrawl.dev/v2/scrape",
        {"url": url, "formats": ["markdown"]},
        {"Authorization": f"Bearer {key('FIRECRAWL_API_KEY')}"},
    )["data"]
    meta = data.get("metadata") or {}
    return Result(url, "firecrawl", meta.get("title"), data.get("markdown") or "", meta.get("statusCode"))


def brightdata(url: str) -> Result:
    _, headers, body = request(
        "https://api.brightdata.com/request",
        {"zone": os.environ.get("BRIGHT_DATA_ZONE", "web_unlocker1"), "url": url, "format": "raw"},
        {"Authorization": f"Bearer {key('BRIGHT_DATA_API_KEY')}"},
    )
    if headers.get("x-brd-error"):
        raise RuntimeError(f"{headers.get('x-brd-error-code')}: {headers['x-brd-error']}")
    status = int(headers.get("x-brd-status-code") or 0) or None
    html = body.decode("utf-8", errors="replace")
    return Result(url, "brightdata", None, markdownify(html, strip=["script", "style"]), status)
