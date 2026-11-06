import html
import os
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlencode

from .net import request, request_json


def _item(author=None, title=None, text="", url=None) -> dict:
    return {"author": author, "title": title, "text": text or "", "url": url}


def _strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or ""))


def hackernews(q: str, n: int) -> list[dict]:
    data = request_json(f"https://hn.algolia.com/api/v1/search?{urlencode({'query': q, 'hitsPerPage': n, 'tags': 'story'})}")
    return [
        _item(h.get("author"), h.get("title"), f"{h.get('points')} points, {h.get('num_comments')} comments",
              h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}")
        for h in data["hits"]
    ]


def wikipedia(q: str, n: int) -> list[dict]:
    params = urlencode({"action": "query", "list": "search", "srsearch": q, "srlimit": n, "format": "json"})
    data = request_json(f"https://en.wikipedia.org/w/api.php?{params}")
    return [
        _item(None, r["title"], _strip_tags(r["snippet"]), f"https://en.wikipedia.org/wiki/{quote(r['title'].replace(' ', '_'))}")
        for r in data["query"]["search"]
    ]


def arxiv(q: str, n: int) -> list[dict]:
    body = request(f"https://export.arxiv.org/api/query?{urlencode({'search_query': f'all:{q}', 'max_results': n})}")[2]
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(body).findall("a:entry", ns):
        authors = [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]
        out.append(_item(", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
                         " ".join(e.findtext("a:title", "", ns).split()), " ".join(e.findtext("a:summary", "", ns).split()),
                         e.findtext("a:id", None, ns)))
    return out


def stackoverflow(q: str, n: int) -> list[dict]:
    params = urlencode({"order": "desc", "sort": "relevance", "q": q, "site": "stackoverflow", "pagesize": n})
    data = request_json(f"https://api.stackexchange.com/2.3/search/advanced?{params}")
    return [
        _item((i.get("owner") or {}).get("display_name"), html.unescape(i["title"]),
              f"score {i['score']}, {i['answer_count']} answers{', answered' if i.get('is_answered') else ''}", i["link"])
        for i in data["items"]
    ]


def github(q: str, n: int) -> list[dict]:
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", **({"Authorization": f"Bearer {token}"} if token else {})}
    data = request_json(f"https://api.github.com/search/repositories?{urlencode({'q': q, 'per_page': n})}", headers=headers)
    return [
        _item(r["owner"]["login"], r["full_name"], f"{r.get('description') or ''} ({r['stargazers_count']} stars)".strip(), r["html_url"])
        for r in data["items"]
    ]


def openalex(q: str, n: int) -> list[dict]:
    data = request_json(f"https://api.openalex.org/works?{urlencode({'search': q, 'per-page': n})}")
    out = []
    for w in data["results"]:
        authors = [a["author"]["display_name"] for a in w.get("authorships", [])]
        out.append(_item(", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""), w.get("title"),
                         f"{w.get('publication_year')}, cited by {w.get('cited_by_count')}", w.get("doi") or w["id"]))
    return out


def bluesky(q: str, n: int) -> list[dict]:
    data = request_json(f"https://api.bsky.app/xrpc/app.bsky.feed.searchPosts?{urlencode({'q': q, 'limit': n})}")
    return [
        _item(p["author"]["handle"], None, p["record"].get("text", ""),
              f"https://bsky.app/profile/{p['author']['handle']}/post/{p['uri'].rsplit('/', 1)[-1]}")
        for p in data["posts"]
    ]


def youtube(q: str, n: int) -> list[dict]:
    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True}) as ydl:
        info = ydl.extract_info(f"ytsearch{n}:{q}", download=False)
    return [
        _item(e.get("channel"), e.get("title"), f"{e.get('duration') or '?'}s, {e.get('view_count') or '?'} views",
              e.get("url") or f"https://www.youtube.com/watch?v={e['id']}")
        for e in info.get("entries", [])
    ]


FREE = {f.__name__: f for f in (hackernews, wikipedia, arxiv, stackoverflow, github, openalex, bluesky, youtube)}
