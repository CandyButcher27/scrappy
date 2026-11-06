# scrappy

A scraping agent for the command line. Give it a URL or a search query; it tries the cheapest
source that can answer, checks that the answer is real content and not a block page, and moves to
the next source when it is not. Output is JSON.

```
$ scrappy fetch https://nopecha.com/demo/cloudflare
attempts: scrapling_http → http 403
          scrapling_browser → http 403
          firecrawl → ok
```

## What it covers

| Target | How scrappy gets it | Verified |
|---|---|---|
| Static pages: articles, docs, wikis, blogs, listings | Scrapling HTTP with a Chrome TLS fingerprint | Wikipedia, books.toscrape.com |
| JavaScript-rendered pages (SPAs) | Scrapling stealth browser, used when the HTTP result lacks the `--expect` text | quotes.toscrape.com/js |
| Pages behind Cloudflare or similar protection | Firecrawl, then Bright Data Web Unlocker | nopecha.com Cloudflare demo (Firecrawl) |
| Reddit posts with comments | Apify `harshmaur~reddit-scraper` | post + 47 comments |
| X (Twitter) posts, text or video | Apify `apidojo~tweet-scraper` | full text, likes, author |
| YouTube videos | yt-dlp: title, channel, stats, description, English captions as plain text | TED-Ed talk transcript |
| Web search | Exa, then Tavily, then SerpAPI | all three keys |

Not covered yet:

- Reddit subreddit or user pages, X profiles, timelines and search. Only single post URLs are
  routed to Apify; other URLs on those sites go through the generic chain and are usually blocked.
- Instagram, TikTok, LinkedIn, Facebook. No route yet; Apify has actors for each.
- Anything behind a login or paywall.
- Videos without captions. The transcript is empty and the description is returned instead.
- Crawling. scrappy fetches one URL per call; following links is up to the caller.
- Structured fields. Pages come back as Markdown; extracting prices, names and so on is up to
  the caller.

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```
pip install uv
git clone https://github.com/CandyButcher27/scrappy
cd scrappy
uv sync
uv run scrapling install    # downloads the browser used by the stealth fetcher
```

## Configure

Create `.env` in the project root. Each key enables one source; a missing key only removes that
source from the chain.

| Variable | Source | Used for | Get it at |
|---|---|---|---|
| `FIRECRAWL_API_KEY` | Firecrawl | protected pages | firecrawl.dev |
| `BRIGHT_DATA_API_KEY` | Bright Data Web Unlocker | protected pages, last resort | brightdata.com |
| `BRIGHT_DATA_ZONE` | Bright Data zone name | optional, default `web_unlocker1` | Bright Data dashboard |
| `APIFY_API_KEY` | Apify | Reddit and X posts | apify.com, Settings → API & Integrations |
| `EXA_API_KEY` | Exa | search | exa.ai |
| `TAVILY_API_KEY` | Tavily | search fallback | tavily.com |
| `SERP_API_KEY` | SerpAPI (Google results) | search fallback | serpapi.com |

```
FIRECRAWL_API_KEY=...
APIFY_API_KEY=...
EXA_API_KEY=...
```

Check that each key works:

```
uv run python evals/keys_check.py
```

## Use

```
uv run scrappy fetch <url> [--expect TEXT] [--via METHOD]
uv run scrappy search "<query>" [-n 5]
uv run scrappy --version
```

- `--expect TEXT` — text that must appear in the result. Use it for JavaScript pages: the HTTP
  fetch returns the page shell without the content, the check fails, and scrappy moves on to the
  browser.
- `--via METHOD` — use only one page method: `scrapling_http`, `scrapling_browser`, `firecrawl`
  or `brightdata`.

Examples:

```
uv run scrappy fetch https://quotes.toscrape.com/js/ --expect "Albert Einstein"
uv run scrappy fetch https://www.reddit.com/r/ClaudeAI/comments/1xotkqg/ive_used_the_big_three_of_the_ai_industry_and/
uv run scrappy fetch https://www.youtube.com/watch?v=QyRqlTV60zM
uv run scrappy search "open source web scraping framework" -n 3
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
 "text": "Markdown of the page, or post body + comments, or video transcript",
 "data": null
}
```

`data` holds the structured record for platform sources: the Reddit post and its comments, the
X post, or the YouTube metadata with its transcript.

`search`:

```json
{
 "ok": true,
 "query": "...",
 "method": "exa",
 "results": [{"title": "...", "url": "...", "snippet": "..."}],
 "attempts": [{"method": "exa", "error": null}]
}
```

## How it works

```
fetch(url)
  Reddit post / X post / YouTube video → platform source → Firecrawl → Bright Data
  anything else → Scrapling HTTP → Scrapling browser → Firecrawl → Bright Data
  after each source: reject HTTP errors, block pages, missing --expect text, near-empty pages

search(query)
  Exa → Tavily → SerpAPI
```

Sources often report success when they failed: a block page returned as 200, or Bright Data
answering 200 with an empty body. The checker in `scrappy/check.py` is what makes the chain
trustworthy; every attempt and its reason is kept in the output.

## Costs

Scrapling and yt-dlp are free. The paid sources all have free tiers, and each call is small:

- Apify runs are capped at $0.50 each (`maxTotalChargeUsd`); the Reddit actor charges $0.02 per run plus a
  per-result fee.
- Firecrawl charges one credit per page.
- Bright Data bills per successful request.

## Use responsibly

scrappy does not read robots.txt and does not rate-limit across calls. Check a site's terms
before scraping it, keep request volume reasonable, and prefer an official API when one exists.

## Development

```
uv run pytest                         # checker, routing and caption parsing
uv run python evals/scrapling_eval.py # live evaluation of the Scrapling fetchers
```
