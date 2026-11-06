from scrappy.agent import chain_for
from scrappy.check import Result, problem
from scrappy.platforms import normalize, platform_for, summarize, vtt_to_text

TEXT = "Real article content. " * 20


def page(text=TEXT, status=200, data=None):
    return Result("https://example.com", "test", None, text, status, data)


def test_good_page_passes():
    assert problem(page()) is None


def test_block_pages_fail():
    assert "block page" in problem(page("Attention Required! | Cloudflare ... " + TEXT))
    assert "block page" in problem(page("You've been blocked by network security. " + TEXT))


def test_short_and_error_pages_fail():
    assert "too little text" in problem(page("Quotes to Scrape Login Next"))
    assert problem(page(status=403)) == "http 403"


def test_expect_text_required():
    assert "not found" in problem(page(), expect="Albert Einstein")
    assert problem(page(TEXT + "by Albert Einstein"), expect="albert einstein") is None


def test_structured_data_skips_text_checks():
    assert problem(page("", data={"post": {"id": 1}})) is None


def test_platform_detection():
    cases = {
        "https://www.reddit.com/r/ClaudeAI/comments/1xotkqg/x/": "reddit",
        "https://www.reddit.com/r/ClaudeAI/": "reddit",
        "https://x.com/Raytar/status/2078098073901834651": "x",
        "https://twitter.com/nasa": "x",
        "https://www.instagram.com/nasa/": "instagram",
        "https://www.tiktok.com/@nasa": "tiktok",
        "https://www.facebook.com/NASA": "facebook",
        "https://www.linkedin.com/jobs/search/?keywords=python": "linkedin",
        "https://youtu.be/QyRqlTV60zM": "youtube",
        "https://www.youtube.com/watch?v=QyRqlTV60zM": "youtube",
        "https://www.dropbox.com/s/abc": None,
        "https://netflix.com/watch/1": None,
    }
    for url, expected in cases.items():
        assert platform_for(url) == expected, url


def test_chain_order():
    assert [n for n, _ in chain_for("https://example.com")] == ["scrapling_http", "scrapling_browser", "firecrawl", "brightdata"]
    assert [n for n, _ in chain_for("https://www.reddit.com/r/ClaudeAI/")] == ["apify_reddit", "firecrawl", "brightdata"]
    assert [n for n, _ in chain_for("https://youtu.be/x")] == ["yt_dlp", "firecrawl", "brightdata"]


def test_normalize_social_items():
    reddit_post = {"title": "Big Three", "body": "My take", "authorName": "u1", "url": "https://reddit.com/p"}
    tweet = {"fullText": "Karpathy lecture", "author": {"userName": "Raytar"}, "twitterUrl": "https://x.com/s/1"}
    tiktok = {"text": "rocket", "authorMeta": {"name": "nasa"}, "webVideoUrl": "https://tiktok.com/v"}
    assert normalize(reddit_post) == {"author": "u1", "title": "Big Three", "text": "My take", "url": "https://reddit.com/p"}
    assert normalize(tweet) == {"author": "Raytar", "title": None, "text": "Karpathy lecture", "url": "https://x.com/s/1"}
    assert normalize(tiktok)["author"] == "nasa"
    assert summarize([reddit_post]) == "[u1] Big Three | My take https://reddit.com/p"


def test_vtt_to_text_drops_timing_and_repeats():
    vtt = "WEBVTT\nKind: captions\n\n00:00.000 --> 00:01.000\nhello <c>there</c>\n\n00:01.000 --> 00:02.000\nhello there\nworld\n"
    assert vtt_to_text(vtt) == "hello there world"


def test_search_on_routes_free_sources_and_reports_failures(monkeypatch):
    import scrappy.agent as agent

    monkeypatch.setitem(agent.FREE, "hackernews", lambda q, n: [{"author": "a", "title": q, "text": "", "url": "u"}])
    out = agent.run_search("rust", 1, on="hackernews")
    assert out["ok"] and out["method"] == "hackernews" and out["results"][0]["title"] == "rust"
    monkeypatch.setitem(agent.FREE, "hackernews", lambda q, n: [])
    assert agent.run_search("rust", 1, on="hackernews")["attempts"] == [{"method": "hackernews", "error": "no results"}]
    assert {"hackernews", "github", "reddit", "x"} <= set(agent.SEARCH_ON)
