import json
import urllib.error
import urllib.request
from pathlib import Path

ENV = dict(
    line.split("=", 1)
    for line in (Path(__file__).parent.parent / ".env").read_text(encoding="utf-8").splitlines()
    if "=" in line and not line.lstrip().startswith("#")
)
ENV = {k.strip(): v.strip().strip('"') for k, v in ENV.items()}


def call(url, headers=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "scraping-agent/0.1", **(headers or {})})
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200].decode(errors="replace")


k = ENV.get
CHECKS = {
    "GITHUB_TOKEN": lambda: call("https://api.github.com/rate_limit", {"Authorization": f"Bearer {k('GITHUB_TOKEN')}"}),
    "GROQ_API_KEY": lambda: call("https://api.groq.com/openai/v1/models", {"Authorization": f"Bearer {k('GROQ_API_KEY')}"}),
    "SERP_API_KEY": lambda: call(f"https://serpapi.com/account?api_key={k('SERP_API_KEY')}"),
    "OPENALEX_API_KEY": lambda: call(f"https://api.openalex.org/works?search=web%20scraping&per-page=1&api_key={k('OPENALEX_API_KEY')}"),
    "YOUTUBE_API_KEY": lambda: call(f"https://www.googleapis.com/youtube/v3/videos?id=QyRqlTV60zM&part=snippet&key={k('YOUTUBE_API_KEY')}"),
    "EXA_API_KEY": lambda: call("https://api.exa.ai/search", {"x-api-key": k("EXA_API_KEY")}, {"query": "web scraping framework", "numResults": 1}),
    "TAVILY_API_KEY": lambda: call("https://api.tavily.com/search", {"Authorization": f"Bearer {k('TAVILY_API_KEY')}"}, {"query": "web scraping framework", "max_results": 1}),
    "FIRECRAWL_API_KEY": lambda: call("https://api.firecrawl.dev/v2/team/credit-usage", {"Authorization": f"Bearer {k('FIRECRAWL_API_KEY')}"}),
    "APIFY_API_KEY": lambda: call("https://api.apify.com/v2/users/me", {"Authorization": f"Bearer {k('APIFY_API_KEY')}"}),
    "BRIGHT_DATA_API_KEY": lambda: call("https://api.brightdata.com/zone/get_active_zones", {"Authorization": f"Bearer {k('BRIGHT_DATA_API_KEY')}"}),
}


def summary(name, data):
    if not isinstance(data, (dict, list)):
        return str(data)[:150]
    match name:
        case "GITHUB_TOKEN": return f"core limit {data['resources']['core']['limit']}"
        case "GROQ_API_KEY": return f"{len(data['data'])} models"
        case "SERP_API_KEY": return f"plan={data.get('plan_name')} searches_left={data.get('total_searches_left')}"
        case "OPENALEX_API_KEY": return f"{data['meta']['count']} works match"
        case "YOUTUBE_API_KEY": return data["items"][0]["snippet"]["title"][:60]
        case "EXA_API_KEY" | "TAVILY_API_KEY": return f"top hit: {data['results'][0]['url']}"
        case "FIRECRAWL_API_KEY": return json.dumps(data.get("data", data))[:120]
        case "APIFY_API_KEY": return f"user={data['data'].get('username')} plan={data['data'].get('plan', {}).get('id')}"
        case "BRIGHT_DATA_API_KEY": return f"zones: {[(z.get('name'), z.get('type')) for z in data]}"


if __name__ == "__main__":
    for name, check in CHECKS.items():
        if not k(name):
            print(f"SKIP {name} (empty)")
            continue
        status, data = check()
        ok = status == 200
        try:
            detail = summary(name, data) if ok else str(data)[:150]
        except (KeyError, IndexError, TypeError) as e:
            detail = f"unexpected shape ({e!r}): {str(data)[:120]}"
        print(f"{'PASS' if ok else 'FAIL'} {name} [{status}] {detail}")
