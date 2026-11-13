import urllib.parse

from .net import key, request_json


def exa(query: str, n: int) -> list[dict]:
    data = request_json(
        "https://api.exa.ai/search",
        {"query": query, "numResults": n, "contents": {"text": {"maxCharacters": 1000}}},
        {"x-api-key": key("EXA_API_KEY")},
    )
    return [{"title": r.get("title"), "url": r["url"], "snippet": r.get("text")} for r in data["results"]]


def tavily(query: str, n: int) -> list[dict]:
    data = request_json(
        "https://api.tavily.com/search",
        {"query": query, "max_results": n},
        {"Authorization": f"Bearer {key('TAVILY_API_KEY')}"},
    )
    return [{"title": r.get("title"), "url": r["url"], "snippet": r.get("content")} for r in data["results"]]


def serpapi(query: str, n: int) -> list[dict]:
    params = urllib.parse.urlencode({"engine": "google", "q": query, "num": n, "api_key": key("SERP_API_KEY")})
    data = request_json(f"https://serpapi.com/search.json?{params}")
    return [{"title": r.get("title"), "url": r["link"], "snippet": r.get("snippet")} for r in data.get("organic_results", [])[:n]]


ENGINES = [exa, tavily, serpapi]
