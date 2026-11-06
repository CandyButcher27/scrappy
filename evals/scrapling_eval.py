import json
import time
from pathlib import Path

from scrapling.fetchers import Fetcher, StealthyFetcher
from scrapling.spiders import Spider, Response

WIKI = "https://en.wikipedia.org/wiki/Web_scraping"
JS_PAGE = "https://quotes.toscrape.com/js/"
CF_PAGE = "https://nopecha.com/demo/cloudflare"
BOOK = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"


def static_http():
    p = Fetcher.get(WIKI, impersonate="chrome")
    title = p.css("h1 ::text").get()
    return title == "Web scraping", f"status={p.status} h1={title!r}"


def markdown():
    p = Fetcher.get(WIKI, impersonate="chrome")
    md = p.markdown(main_content_only=True)
    return len(md) > 5000 and "scraping" in md.lower(), f"{len(md)} chars, head={md[:80]!r}"


def js_http_control():
    p = Fetcher.get(JS_PAGE, impersonate="chrome")
    n = len(p.css(".quote"))
    return n == 0, f"{n} quotes (expected 0 without JS)"


def js_browser():
    p = StealthyFetcher.fetch(JS_PAGE, headless=True, wait_selector=".quote")
    n = len(p.css(".quote"))
    return n == 10, f"{n} quotes"


def cloudflare_http_control():
    p = Fetcher.get(CF_PAGE, impersonate="chrome")
    n = len(p.css("#padded_content a"))
    return True, f"status={p.status} links={n} (informational)"


def cloudflare_browser():
    p = StealthyFetcher.fetch(CF_PAGE, headless=True, solve_cloudflare=True)
    n = len(p.css("#padded_content a"))
    return n > 0, f"status={p.status} links={n}"


def structured():
    p = Fetcher.get(BOOK, impersonate="chrome")
    table = {r.css("th::text").get(): r.css("td::text").get() for r in p.css("table.table tr")}
    item = {
        "title": p.css(".product_main h1::text").get(),
        "price": p.css(".product_main .price_color::text").get(),
        "upc": table.get("UPC"),
        "stock": table.get("Availability"),
    }
    ok = item["title"] == "A Light in the Attic" and item["upc"] == "a897fe39b1053632"
    return ok, json.dumps(item)


class Quotes(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]
    robots_txt_obey = True
    concurrent_requests = 2
    download_delay = 0.5

    async def parse(self, response: Response):
        for q in response.css(".quote"):
            yield {"text": q.css(".text::text").get(), "author": q.css(".author::text").get()}
        nxt = response.css(".next a")
        if nxt:
            yield response.follow(nxt[0].attrib["href"])


def pagination_spider():
    items = Quotes().start().items
    return len(items) == 100, f"{len(items)} quotes over 10 pages"


TESTS = [static_http, markdown, js_http_control, js_browser,
         cloudflare_http_control, cloudflare_browser, structured, pagination_spider]

if __name__ == "__main__":
    import sys
    selected = [t for t in TESTS if not sys.argv[1:] or t.__name__ in sys.argv[1:]]
    results = []
    for test in selected:
        start = time.perf_counter()
        try:
            ok, detail = test()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        secs = round(time.perf_counter() - start, 1)
        results.append({"test": test.__name__, "pass": ok, "secs": secs, "detail": detail})
        print(f"{'PASS' if ok else 'FAIL'} {test.__name__} ({secs}s) {detail[:150]}", flush=True)
    out = Path(__file__).parent / "results" / "scrapling.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
