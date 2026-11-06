# scrappy

A scraping agent for the command line and for AI tools. Give it a URL, a search query or a site to
crawl; it tries the cheapest source that can answer, checks that the answer is real content and not
a block page, and moves to the next source when it is not. Output is JSON.

Use it three ways:

- as an **MCP server**, so Claude Code, Cursor, Claude Desktop or any MCP client can call `fetch`,
  `search` and `crawl` as tools
- from the **command line** with `npx scrappy-agent` or `uvx scrappy-agent`
- as a **Python library** (`from scrappy import agent`)

```
$ npx scrappy-agent fetch https://nopecha.com/demo/cloudflare
attempts: scrapling_http → http 403
          scrapling_browser → http 403
          firecrawl → ok
```

## What it covers

| Target | Source | Verified with |
|---|---|---|
| Static pages: articles, docs, wikis, blogs, listings | Scrapling HTTP with a Chrome TLS fingerprint | Wikipedia, books.toscrape.com |
| JavaScript-rendered pages | Scrapling stealth browser, when the HTTP result lacks the `--expect` text | quotes.toscrape.com/js |
| Pages behind Cloudflare or similar | Firecrawl, then Bright Data Web Unlocker | nopecha.com Cloudflare demo |
| Whole sites | `crawl`: same-host links, breadth-first, robots.txt obeyed, duplicates dropped | books.toscrape.com |
| Reddit posts with comments, subreddits, user pages, search | Apify `harshmaur~reddit-scraper` | a post with 47 comments, r/ClaudeAI, search |
| X posts, profiles, search | Apify `apidojo~tweet-scraper` | a post, a profile, search |
| Instagram profiles, posts, hashtags | Apify `apify~instagram-scraper` | @nasa, #webscraping |
| TikTok profiles, videos, search | Apify `clockworks~tiktok-scraper` | @nasa, search |
| Facebook pages | Apify `apify~facebook-posts-scraper` | facebook.com/NASA |
| LinkedIn job searches, post search | Apify `curious_coder~linkedin-jobs-scraper`, `harvestapi~linkedin-post-search` | jobs URL, search |
| YouTube videos | yt-dlp: title, channel, stats, description and English captions as text | TED-Ed talk |
| Web search | Exa, then Tavily, then Google results via SerpAPI | all three |

### Search sources (`search --on`)

| `--on` | Searches | Needs |
|---|---|---|
| `hackernews` | Hacker News stories (Algolia API) | nothing |
| `wikipedia` | English Wikipedia articles | nothing |
| `arxiv` | arXiv papers with abstracts | nothing |
| `openalex` | research papers across disciplines, with citation counts | nothing |
| `stackoverflow` | Stack Overflow questions | nothing |
| `github` | GitHub repositories | nothing (`GITHUB_TOKEN` raises the rate limit) |
| `bluesky` | Bluesky posts | nothing |
| `youtube` | YouTube videos (yt-dlp, no API quota) | nothing |
| `reddit` | Reddit posts | `APIFY_API_KEY` |
| `x` | X posts | `APIFY_API_KEY` |
| `instagram` | posts under a hashtag | `APIFY_API_KEY` |
| `tiktok` | TikTok videos | `APIFY_API_KEY` |
| `linkedin` | LinkedIn posts | `APIFY_API_KEY` |

All 13 were verified live.

Not covered:

- Anything behind a login or paywall, and private accounts.
- LinkedIn profiles of individuals, by design.
- Facebook search.
- Videos without captions: the transcript is empty and the description is returned instead.
- Structured fields (prices, names): pages come back as Markdown for the caller or the LLM to read.

## Install

scrappy is a Python package. Both commands below fetch and run the published release; `npx`
installs [uv](https://docs.astral.sh/uv/) first if it is missing.

```
npx scrappy-agent --version
uvx scrappy-agent --version
```

Then run the setup once:

```
npx scrappy-agent setup
```

It asks for each API key below, shows where to get it, tests it with one cheap call, and saves
the keys to `~/.scrappy/.env`. Press Enter to skip a key; that source is simply left out. It then
offers to download the stealth browser for JavaScript-heavy pages (without it, scrappy moves on
to Firecrawl for those pages).

Test the saved keys at any time:

```
npx scrappy-agent setup --check
```

## API keys

Each key enables one source; a missing key only removes that source from the chain. scrappy
reads, in order: environment variables, `./.env`, then `~/.scrappy/.env` (written by `setup`).

| Variable | Source | Used for | Get it at |
|---|---|---|---|
| `APIFY_API_KEY` | Apify | Reddit, X, Instagram, TikTok, Facebook, LinkedIn | apify.com, Settings → API & Integrations |
| `FIRECRAWL_API_KEY` | Firecrawl | protected pages | firecrawl.dev |
| `BRIGHT_DATA_API_KEY` | Bright Data Web Unlocker | protected pages, last resort | brightdata.com |
| `BRIGHT_DATA_ZONE` | Bright Data zone name | optional, default `web_unlocker1` | Bright Data dashboard |
| `EXA_API_KEY` | Exa | search | exa.ai |
| `TAVILY_API_KEY` | Tavily | search fallback | tavily.com |
| `SERP_API_KEY` | SerpAPI (Google results) | search fallback | serpapi.com |

```
# ~/.scrappy/.env
APIFY_API_KEY=...
FIRECRAWL_API_KEY=...
EXA_API_KEY=...
```

Static pages, crawling, YouTube and the eight free search sources work with no keys at all.

## Use as an MCP server

Claude Code:

```
claude mcp add scrappy -- npx -y scrappy-agent mcp
```

Cursor, Claude Desktop and other clients (`mcpServers` in their config file):

```json
{
  "mcpServers": {
    "scrappy": {
      "command": "npx",
      "args": ["-y", "scrappy-agent", "mcp"],
      "env": { "APIFY_API_KEY": "...", "FIRECRAWL_API_KEY": "...", "EXA_API_KEY": "..." }
    }
  }
}
```

Keys can go in the `env` block or in `~/.scrappy/.env`. Use `"command": "uvx", "args":
["scrappy-agent", "mcp"]` to skip Node.

Tools:

| Tool | Arguments | Returns |
|---|---|---|
| `fetch` | `url`, `expect`, `limit` (posts/comments, default 20), `max_chars` (default 20000), `include_data` | text of the page, posts or transcript, plus every attempt |
| `search` | `query`, `n` (default 5), `on` (any source in the table above) | results with title or author, text and URL |
| `crawl` | `url`, `limit` (default 10), `depth` (default 2), `max_chars_per_page` (default 3000) | pages with title and text, skipped URLs with reasons |

## Use from the command line

```
scrappy fetch <url> [--expect TEXT] [--via METHOD] [--limit N]
scrappy search "<query>" [-n 5] [--on SOURCE]
scrappy crawl <url> [--limit 20] [--depth 2] [--delay 1]
scrappy mcp
scrappy setup
scrappy --version
```

Prefix with `npx scrappy-agent` or `uvx scrappy-agent` (the commands are `scrappy` and
`scrappy-agent` once installed).

- `--expect TEXT`: text that must appear in the result. Use it for JavaScript pages: the HTTP fetch
  returns the page shell without the content, the check fails, and scrappy moves to the browser.
- `--via METHOD`: use only one page method: `scrapling_http`, `scrapling_browser`, `firecrawl` or
  `brightdata`.
- `--limit N`: for social URLs, the number of posts, or comments on a single post.

Examples:

```
scrappy fetch https://quotes.toscrape.com/js/ --expect "Albert Einstein"
scrappy fetch https://www.reddit.com/r/ClaudeAI/ --limit 10
scrappy fetch https://www.instagram.com/nasa/ --limit 5
scrappy fetch https://www.youtube.com/watch?v=QyRqlTV60zM
scrappy search "claude code" --on reddit -n 10
scrappy search "vector databases" --on hackernews
scrappy search "open source web scraping framework"
scrappy crawl https://books.toscrape.com/ --limit 30 --depth 2
```

The exit code is 0 when a source succeeded and 1 when every source failed.

### Output

`fetch`:

```json
{
 "ok": true,
 "url": "https://...",
 "attempts": [{"method": "scrapling_http", "error": "expected text 'Albert Einstein' not found"},
              {"method": "scrapling_browser", "error": null}],
 "method": "scrapling_browser",
 "title": "Quotes to Scrape",
 "status": 200,
 "text": "Markdown of the page, posts as '[author] text url', or a video transcript",
 "data": null
}
```

`data` holds the raw platform records (posts, comments, video metadata). `search` returns
`results: [{title, url, snippet}]` for the web and `results: [{author, title, text, url}]` with
`--on`. `crawl` returns `pages: [{url, title, text}]` and `skipped: [{url, error}]`.

## How it works

```
fetch(url)
  YouTube              → yt-dlp                  → Firecrawl → Bright Data
  Reddit, X, Instagram,
  TikTok, Facebook,
  LinkedIn             → Apify actor             → Firecrawl → Bright Data
  anything else        → Scrapling HTTP → Scrapling browser → Firecrawl → Bright Data
  after each source: reject HTTP errors, block pages, missing --expect text, near-empty pages

search(query)          → Exa → Tavily → SerpAPI, or one source with --on
crawl(url)             → fetch the start URL, then reuse the method that worked for every page
```

Sources often report success when they failed: a block page returned as 200, or Bright Data
answering 200 with an empty body. The checker in `scrappy/check.py` is what makes the chain
trustworthy; every attempt and its reason is kept in the output.

## Costs

Scrapling, yt-dlp and crawling are free. The paid sources have free tiers:

- Apify runs are capped at $0.50 each. Most actors charge a small start fee plus a fee per item,
  so `--limit` controls the cost. Apify's free plan includes $5 of credit a month.
- Firecrawl charges one credit per page, so a crawl that falls back to Firecrawl costs one credit
  per page crawled.
- Bright Data bills per successful request.

## Use responsibly

`crawl` obeys robots.txt and waits between requests; `fetch` does neither. Check a site's terms
before scraping it, keep volume reasonable, and prefer an official API when one exists. Social
data is fetched through Apify's public scrapers, not through your own accounts.

## Development

```
git clone https://github.com/CandyButcher27/scrappy && cd scrappy
uv sync
uv run pytest
uv run scrappy fetch https://books.toscrape.com/
SCRAPPY_FROM=. node npm/bin/scrappy.js --version   # run the npm wrapper against the local checkout
```

Releases: bump the version in `pyproject.toml` and `npm/package.json`, then push a `vX.Y.Z` tag.
The release workflow tests, publishes to PyPI and npm, and creates the GitHub release.

## License

MIT
