from importlib.metadata import version

from mcp.server.mcpserver import MCPServer

from . import agent

server = MCPServer(
    "scrappy",
    version=version("scrappy-agent"),
    instructions=(
        "Web and social scraping. fetch reads one URL (pages, Reddit, X, Instagram, TikTok, Facebook, LinkedIn jobs, "
        "YouTube transcripts), trying cheap sources first and checking each result is real content. search finds pages "
        "on the web, or with `on` searches one source: Hacker News, Wikipedia, arXiv, Stack Overflow, GitHub, OpenAlex, "
        "Bluesky, YouTube, Reddit, X, Instagram, TikTok or LinkedIn. crawl follows links within one site. Every result lists "
        "the attempts made; paid sources (Firecrawl, Bright Data, Apify) are used only when free ones fail."
    ),
)


def _clip(text: str | None, max_chars: int) -> str | None:
    if text and len(text) > max_chars:
        return text[:max_chars] + f"\n[truncated {len(text) - max_chars} chars]"
    return text


@server.tool()
def fetch(url: str, expect: str | None = None, limit: int = 20, max_chars: int = 20000, include_data: bool = False) -> dict:
    """Fetch one URL as Markdown or, for social and video URLs, as posts / transcript.

    expect: text that must appear in the result; when it is missing the next source is tried (use it for
    JavaScript-heavy pages). limit: max posts or comments for social URLs. include_data: also return the raw
    platform records.
    """
    out = agent.run_fetch(url, expect, None, limit)
    out["text"] = _clip(out.get("text"), max_chars)
    if not include_data:
        out.pop("data", None)
    return out


@server.tool()
def search(query: str, n: int = 5, on: str | None = None) -> dict:
    """Search the web (Exa, then Tavily, then Google via SerpAPI), or one source when `on` is set.

    on, free: hackernews, wikipedia, arxiv, stackoverflow, github (repositories), openalex (research papers),
    bluesky, youtube. on, through Apify: reddit, x, instagram (hashtag), tiktok, linkedin (posts).
    """
    if on and on not in agent.SEARCH_ON:
        return {"ok": False, "error": f"on must be one of {agent.SEARCH_ON}"}
    out = agent.run_search(query, n, on)
    out.pop("data", None)
    return out


@server.tool()
def crawl(url: str, limit: int = 10, depth: int = 2, max_chars_per_page: int = 3000) -> dict:
    """Crawl one site from a start URL, following same-host links breadth-first and obeying robots.txt."""
    out = agent.run_crawl(url, limit, depth)
    for page in out["pages"]:
        page["text"] = _clip(page["text"], max_chars_per_page)
    return out


def main() -> None:
    server.run("stdio")
