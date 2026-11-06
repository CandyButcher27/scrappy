from .check import Result, problem
from .pages import brightdata, firecrawl, scrapling_browser, scrapling_http
from .platforms import platform_for
from .search import ENGINES

PAGE_CHAIN = [scrapling_http, scrapling_browser, firecrawl, brightdata]
METHODS = {f.__name__: f for f in PAGE_CHAIN}


def chain_for(url: str) -> list:
    platform = platform_for(url)
    # Platform pages block local fetches outright, so their fallback skips straight to the paid unlockers.
    return [platform, firecrawl, brightdata] if platform else PAGE_CHAIN


def fetch(url: str, expect: str | None = None, via: str | None = None) -> tuple[Result | None, list[dict]]:
    attempts = []
    for method in [METHODS[via]] if via else chain_for(url):
        try:
            result = method(url)
            reason = problem(result, expect)
        except Exception as e:
            result, reason = None, f"{type(e).__name__}: {e}"
        attempts.append({"method": method.__name__, "error": reason})
        if reason is None:
            return result, attempts
    return None, attempts


def search(query: str, n: int = 5) -> tuple[str | None, list[dict], list[dict]]:
    attempts = []
    for engine in ENGINES:
        try:
            results = engine(query, n)
            reason = None if results else "no results"
        except Exception as e:
            results, reason = [], f"{type(e).__name__}: {e}"
        attempts.append({"method": engine.__name__, "error": reason})
        if reason is None:
            return engine.__name__, results, attempts
    return None, [], attempts
