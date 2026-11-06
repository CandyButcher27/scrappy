import re
import time
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

from .check import Result, problem
from .net import request
from .pages import brightdata, firecrawl, scrapling_browser, scrapling_http
from .platforms import fetch_platform, normalize, platform_for, social_search
from .search import ENGINES

PAGE_CHAIN = [scrapling_http, scrapling_browser, firecrawl, brightdata]
METHODS = {f.__name__: f for f in PAGE_CHAIN}
SKIP_EXT = re.compile(r"\.(?:png|jpe?g|gif|svg|webp|ico|css|js|pdf|zip|gz|mp4|mp3|woff2?)(?:\?|$)", re.I)


def chain_for(url: str, limit: int = 20) -> list[tuple[str, callable]]:
    platform = platform_for(url)
    page_chain = [(f.__name__, f) for f in PAGE_CHAIN]
    if not platform:
        return page_chain
    # Platform sites block local fetches outright, so their fallback skips straight to the paid unlockers.
    first = "yt_dlp" if platform == "youtube" else f"apify_{platform}"
    return [(first, lambda u: fetch_platform(platform, u, limit))] + page_chain[2:]


def fetch(url: str, expect: str | None = None, via: str | None = None, limit: int = 20) -> tuple[Result | None, list[dict]]:
    attempts = []
    for name, method in [(via, METHODS[via])] if via else chain_for(url, limit):
        try:
            result = method(url)
            reason = problem(result, expect)
        except Exception as e:
            result, reason = None, f"{type(e).__name__}: {e}"
        attempts.append({"method": name, "error": reason})
        if reason is None:
            return result, attempts
    return None, attempts


def run_fetch(url: str, expect: str | None = None, via: str | None = None, limit: int = 20) -> dict:
    result, attempts = fetch(url, expect, via, limit)
    out = {"ok": result is not None, "url": url, "attempts": attempts}
    if result:
        out |= {"method": result.method, "title": result.title, "status": result.status, "text": result.text, "data": result.data}
    return out


def run_search(query: str, n: int = 5, on: str | None = None) -> dict:
    if on:
        try:
            result = social_search(on, query, n)
        except Exception as e:
            return {"ok": False, "query": query, "on": on, "results": [], "attempts": [{"method": f"apify_{on}", "error": f"{type(e).__name__}: {e}"}]}
        return {"ok": True, "query": query, "on": on, "method": result.method, "results": [normalize(i) for i in result.data],
                "data": result.data, "attempts": [{"method": result.method, "error": None}]}
    attempts = []
    for engine in ENGINES:
        try:
            results = engine(query, n)
            reason = None if results else "no results"
        except Exception as e:
            results, reason = [], f"{type(e).__name__}: {e}"
        attempts.append({"method": engine.__name__, "error": reason})
        if reason is None:
            return {"ok": True, "query": query, "method": engine.__name__, "results": results, "attempts": attempts}
    return {"ok": False, "query": query, "method": None, "results": [], "attempts": attempts}


def _robots(start: str) -> RobotFileParser | None:
    parser = RobotFileParser()
    try:
        parser.parse(request(urljoin(start, "/robots.txt"), timeout=15)[2].decode("utf-8", errors="replace").splitlines())
    except Exception:
        return None
    return parser


def run_crawl(start: str, limit: int = 20, depth: int = 2, expect: str | None = None, delay: float = 1.0) -> dict:
    first, attempts = fetch(start, expect)
    if not first:
        return {"ok": False, "start": start, "attempts": attempts, "pages": [], "skipped": []}
    page = lambda r: {"url": r.url, "title": r.title, "text": r.text}  # noqa: E731
    if first.method not in METHODS:
        return {"ok": True, "start": start, "method": first.method, "attempts": attempts, "pages": [page(first)], "skipped": [],
                "note": "platform URLs are not crawled; use fetch with a higher limit"}
    method, host, robots = METHODS[first.method], urlparse(start).netloc, _robots(start)
    pages, skipped = [page(first)], []
    seen, seen_text = {urldefrag(start).url}, {first.text}
    queue = deque((link, 1) for link in first.links)
    while queue and len(pages) < limit:
        url, level = queue.popleft()
        url = urldefrag(url).url
        if url in seen or level > depth or urlparse(url).netloc != host or SKIP_EXT.search(url):
            continue
        seen.add(url)
        if robots and not robots.can_fetch("*", url):
            skipped.append({"url": url, "error": "disallowed by robots.txt"})
            continue
        time.sleep(delay)
        try:
            result = method(url)
            reason = problem(result)
        except Exception as e:
            result, reason = None, f"{type(e).__name__}: {e}"
        if not reason and result.text in seen_text:
            reason = "duplicate of a page already crawled"
        if reason:
            skipped.append({"url": url, "error": reason})
            continue
        seen_text.add(result.text)
        pages.append(page(result))
        queue.extend((link, level + 1) for link in result.links)
    return {"ok": True, "start": start, "method": first.method, "attempts": attempts, "pages": pages, "skipped": skipped}
