import re

from .check import Result
from .net import key, request, request_json


def apify(actor: str, body: dict, max_usd: float = 0.5) -> list:
    return request_json(
        f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items?maxTotalChargeUsd={max_usd}&timeout=180",
        body,
        {"Authorization": f"Bearer {key('APIFY_API_KEY')}"},
        timeout=200,
    )


def reddit(url: str) -> Result:
    items = apify(
        "harshmaur~reddit-scraper",
        {"startUrls": [{"url": url}], "maxPostsCount": 1, "crawlCommentsPerPost": True, "maxCommentsPerPost": 50},
    )
    post = next(i for i in items if i.get("dataType") == "post")
    comments = [i for i in items if i.get("dataType") == "comment"]
    text = "\n\n".join([post.get("body") or ""] + [f"{c.get('authorName')}: {c.get('body')}" for c in comments])
    return Result(url, "apify_reddit", post.get("title"), text, None, {"post": post, "comments": comments})


def x_post(url: str) -> Result:
    items = apify("apidojo~tweet-scraper", {"startUrls": [url], "maxItems": 1})
    if not items or items[0].get("noResults"):
        raise RuntimeError("no post returned")
    post = items[0]
    return Result(url, "apify_x", (post.get("author") or {}).get("userName"), post.get("fullText") or post.get("text") or "", None, post)


def youtube(url: str) -> Result:
    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    captions = (info.get("subtitles") or {}) | {
        lang: tracks for lang, tracks in (info.get("automatic_captions") or {}).items() if lang not in (info.get("subtitles") or {})
    }
    transcript = ""
    for lang in ("en", "en-orig", "en-US", "en-GB"):
        vtt = next((t["url"] for t in captions.get(lang, []) if t.get("ext") == "vtt"), None)
        if vtt:
            transcript = vtt_to_text(request(vtt)[2].decode("utf-8", errors="replace"))
            break
    meta = {k: info.get(k) for k in ("id", "title", "channel", "upload_date", "duration", "view_count", "like_count", "description")}
    meta["transcript"] = transcript
    return Result(url, "yt_dlp", info.get("title"), transcript or info.get("description") or "", None, meta)


def vtt_to_text(vtt: str) -> str:
    lines = []
    for line in vtt.splitlines():
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:")) or line.isdigit():
            continue
        if not lines or lines[-1] != line:
            lines.append(line)
    return " ".join(lines)


ROUTES = [
    (re.compile(r"reddit\.com/r/[^/]+/comments/"), reddit),
    (re.compile(r"(?:^|//|\.)(?:x|twitter)\.com/[^/]+/status/\d+"), x_post),
    (re.compile(r"youtube\.com/(?:watch|shorts/)|youtu\.be/"), youtube),
]


def platform_for(url: str):
    return next((handler for pattern, handler in ROUTES if pattern.search(url)), None)
