import re

from .check import Result
from .net import key, request, request_json

MAX_USD_PER_RUN = 0.5


def apify(actor: str, body: dict) -> list:
    items = request_json(
        f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items?maxTotalChargeUsd={MAX_USD_PER_RUN}&timeout=240",
        body,
        {"Authorization": f"Bearer {key('APIFY_API_KEY')}"},
        timeout=260,
    )
    real = [i for i in items if not (i.get("error") or i.get("noResults"))]
    if not real:
        raise RuntimeError(f"{actor} returned no items: {str(items[:1])[:200]}")
    return real


def _reddit_url(url: str, n: int):
    if "/comments/" in url:
        body = {"startUrls": [{"url": url}], "maxPostsCount": 1, "crawlCommentsPerPost": True, "maxCommentsPerPost": n}
    else:
        body = {"startUrls": [{"url": url}], "maxPostsCount": n, "crawlCommentsPerPost": False}
    return "harshmaur~reddit-scraper", body


def _tiktok_url(url: str, n: int):
    if "/video/" in url:
        return "clockworks~tiktok-scraper", {"postURLs": [url]}
    profile = re.search(r"tiktok\.com/@([^/?#]+)", url)
    if not profile:
        raise ValueError("only TikTok video and @profile URLs are supported")
    return "clockworks~tiktok-scraper", {"profiles": [profile.group(1)], "resultsPerPage": n}


def _linkedin_url(url: str, n: int):
    if "/jobs/" not in url:
        raise ValueError("only LinkedIn job URLs are supported; use search for posts")
    return "curious_coder~linkedin-jobs-scraper", {"urls": [url], "limitPerSource": n, "scrapeCompany": False}


PREFIX = r"(?:^|//|\.)"
SOCIAL = {
    "reddit": {
        "pattern": PREFIX + r"(?:reddit\.com|redd\.it)/",
        "url": _reddit_url,
        "search": lambda q, n: ("harshmaur~reddit-scraper", {"searchTerms": [q], "searchPosts": True, "searchSort": "relevance", "maxPostsCount": n}),
    },
    "x": {
        "pattern": PREFIX + r"(?:x|twitter)\.com/",
        "url": lambda u, n: ("apidojo~tweet-scraper", {"startUrls": [u], "maxItems": n}),
        "search": lambda q, n: ("apidojo~tweet-scraper", {"searchTerms": [q], "maxItems": n, "sort": "Latest"}),
    },
    "instagram": {
        "pattern": PREFIX + r"instagram\.com/",
        "url": lambda u, n: ("apify~instagram-scraper", {"directUrls": [u], "resultsType": "posts", "resultsLimit": n}),
        "search": lambda q, n: (
            "apify~instagram-scraper",
            {"directUrls": [f"https://www.instagram.com/explore/tags/{re.sub(r'[^\w]', '', q)}/"], "resultsType": "posts", "resultsLimit": n},
        ),
    },
    "tiktok": {
        "pattern": PREFIX + r"tiktok\.com/",
        "url": _tiktok_url,
        "search": lambda q, n: ("clockworks~tiktok-scraper", {"searchQueries": [q], "resultsPerPage": n}),
    },
    "facebook": {
        "pattern": PREFIX + r"facebook\.com/",
        "url": lambda u, n: ("apify~facebook-posts-scraper", {"startUrls": [{"url": u}], "resultsLimit": n}),
        "search": None,
    },
    "linkedin": {
        "pattern": PREFIX + r"linkedin\.com/",
        "url": _linkedin_url,
        "search": lambda q, n: ("harvestapi~linkedin-post-search", {"searchQueries": [q], "maxPosts": n}),
    },
}
SEARCHABLE = [name for name, p in SOCIAL.items() if p["search"]]
YOUTUBE = re.compile(r"youtube\.com/(?:watch|shorts/)|youtu\.be/")

BODY_KEYS = ("fullText", "text", "caption", "body", "descriptionText", "description", "content")
URL_KEYS = ("url", "postUrl", "webVideoUrl", "twitterUrl", "link", "jobUrl")


def _author(item: dict) -> str | None:
    for k in ("authorName", "ownerUsername", "username", "companyName", "pageName"):
        if isinstance(item.get(k), str):
            return item[k]
    for k in ("author", "authorMeta", "user"):
        v = item.get(k)
        if isinstance(v, dict):
            return v.get("userName") or v.get("name") or v.get("username")
        if isinstance(v, str):
            return v
    return None


def normalize(item: dict) -> dict:
    title = item.get("title") if isinstance(item.get("title"), str) else None
    body = next((item[k] for k in BODY_KEYS if isinstance(item.get(k), str) and item[k].strip()), "")
    url = next((item[k] for k in URL_KEYS if isinstance(item.get(k), str)), None)
    return {"author": _author(item), "title": title, "text": body.strip(), "url": url}


def summarize(items: list[dict]) -> str:
    lines = []
    for n in map(normalize, items):
        text = " | ".join(p for p in (n["title"], n["text"]) if p)
        lines.append(f"[{n['author'] or '?'}] {text} {n['url'] or ''}".strip())
    return "\n\n".join(lines)


def _as_result(target: str, platform: str, items: list[dict]) -> Result:
    title = next((i["title"] for i in items if isinstance(i.get("title"), str)), None)
    return Result(target, f"apify_{platform}", title, summarize(items), None, items)


def social_fetch(platform: str, url: str, limit: int = 20) -> Result:
    actor, body = SOCIAL[platform]["url"](url, limit)
    return _as_result(url, platform, apify(actor, body))


def social_search(platform: str, query: str, limit: int = 20) -> Result:
    if platform not in SEARCHABLE:
        raise ValueError(f"search is not available on {platform}; searchable: {', '.join(SEARCHABLE)}")
    actor, body = SOCIAL[platform]["search"](query, limit)
    return _as_result(query, platform, apify(actor, body))


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


def platform_for(url: str) -> str | None:
    if YOUTUBE.search(url):
        return "youtube"
    return next((name for name, p in SOCIAL.items() if re.search(p["pattern"], url)), None)


def fetch_platform(platform: str, url: str, limit: int = 20) -> Result:
    return youtube(url) if platform == "youtube" else social_fetch(platform, url, limit)
