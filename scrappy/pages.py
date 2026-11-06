import os
from urllib.parse import urljoin

from markdownify import markdownify

from .check import Result
from .net import key, request, request_json


def _links(base: str, hrefs) -> list[str]:
    return [urljoin(base, h) for h in hrefs if h and not h.startswith(("#", "javascript:", "mailto:", "tel:"))]


def _from_scrapling(url: str, method: str, page) -> Result:
    links = _links(url, page.css("a::attr(href)").getall())
    title = " ".join((page.css("title::text").get() or "").split()) or None
    return Result(url, method, title, page.markdown(), page.status, links=links)


def scrapling_http(url: str) -> Result:
    from scrapling.fetchers import Fetcher

    return _from_scrapling(url, "scrapling_http", Fetcher.get(url, impersonate="chrome"))


def scrapling_browser(url: str) -> Result:
    from scrapling.fetchers import StealthyFetcher

    return _from_scrapling(url, "scrapling_browser", StealthyFetcher.fetch(url, headless=True, network_idle=True))


def firecrawl(url: str) -> Result:
    data = request_json(
        "https://api.firecrawl.dev/v2/scrape",
        {"url": url, "formats": ["markdown", "links"]},
        {"Authorization": f"Bearer {key('FIRECRAWL_API_KEY')}"},
    )["data"]
    meta = data.get("metadata") or {}
    return Result(url, "firecrawl", meta.get("title"), data.get("markdown") or "", meta.get("statusCode"), links=data.get("links") or [])


def brightdata(url: str) -> Result:
    from scrapling.parser import Selector

    _, headers, body = request(
        "https://api.brightdata.com/request",
        {"zone": os.environ.get("BRIGHT_DATA_ZONE", "web_unlocker1"), "url": url, "format": "raw"},
        {"Authorization": f"Bearer {key('BRIGHT_DATA_API_KEY')}"},
    )
    if headers.get("x-brd-error"):
        raise RuntimeError(f"{headers.get('x-brd-error-code')}: {headers['x-brd-error']}")
    status = int(headers.get("x-brd-status-code") or 0) or None
    html = body.decode("utf-8", errors="replace")
    page = Selector(html)
    return Result(
        url, "brightdata", page.css("title::text").get(), markdownify(html, strip=["script", "style"]), status,
        links=_links(url, page.css("a::attr(href)").getall()),
    )
