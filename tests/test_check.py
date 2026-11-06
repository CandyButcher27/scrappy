from scrappy.agent import PAGE_CHAIN, chain_for
from scrappy.check import Result, problem
from scrappy.pages import brightdata, firecrawl
from scrappy.platforms import reddit, vtt_to_text, x_post, youtube

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


def test_routing():
    assert chain_for("https://www.reddit.com/r/ClaudeAI/comments/1xotkqg/x/") == [reddit, firecrawl, brightdata]
    assert chain_for("https://x.com/Raytar/status/2078098073901834651")[0] is x_post
    assert chain_for("https://twitter.com/a/status/1")[0] is x_post
    assert chain_for("https://youtu.be/QyRqlTV60zM")[0] is youtube
    assert chain_for("https://www.youtube.com/watch?v=QyRqlTV60zM")[0] is youtube
    assert chain_for("https://www.reddit.com/r/ClaudeAI/") == PAGE_CHAIN
    assert chain_for("https://netflix.com/watch/1") == PAGE_CHAIN


def test_vtt_to_text_drops_timing_and_repeats():
    vtt = "WEBVTT\nKind: captions\n\n00:00.000 --> 00:01.000\nhello <c>there</c>\n\n00:01.000 --> 00:02.000\nhello there\nworld\n"
    assert vtt_to_text(vtt) == "hello there world"
