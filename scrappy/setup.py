import os
import sys
from getpass import getpass
from pathlib import Path

from .net import request_json

ENV_FILE = Path.home() / ".scrappy" / ".env"


def _apify(k):
    return "user " + request_json("https://api.apify.com/v2/users/me", headers={"Authorization": f"Bearer {k}"})["data"]["username"]


def _firecrawl(k):
    data = request_json("https://api.firecrawl.dev/v2/team/credit-usage", headers={"Authorization": f"Bearer {k}"})["data"]
    return f"{data['remainingCredits']} credits left"


def _brightdata(k):
    zones = request_json("https://api.brightdata.com/zone/get_active_zones", headers={"Authorization": f"Bearer {k}"})
    unlockers = [z["name"] for z in zones if z.get("type") == "unblocker"]
    if not unlockers:
        raise RuntimeError("no Web Unlocker zone; create one in the Bright Data dashboard")
    return f"unlocker zones: {', '.join(unlockers)}"


def _exa(k):
    request_json("https://api.exa.ai/search", {"query": "test", "numResults": 1}, {"x-api-key": k})
    return "search works"


def _tavily(k):
    request_json("https://api.tavily.com/search", {"query": "test", "max_results": 1}, {"Authorization": f"Bearer {k}"})
    return "search works"


def _serpapi(k):
    return f"{request_json(f'https://serpapi.com/account?api_key={k}')['total_searches_left']} searches left"


KEYS = [
    ("APIFY_API_KEY", "Apify", "Reddit, X, Instagram, TikTok, Facebook and LinkedIn", "https://console.apify.com/settings/integrations", _apify),
    ("FIRECRAWL_API_KEY", "Firecrawl", "pages behind Cloudflare and other bot protection", "https://www.firecrawl.dev/app/api-keys", _firecrawl),
    ("BRIGHT_DATA_API_KEY", "Bright Data", "last-resort unblocking of protected pages", "https://brightdata.com/cp", _brightdata),
    ("EXA_API_KEY", "Exa", "web search", "https://dashboard.exa.ai/api-keys", _exa),
    ("TAVILY_API_KEY", "Tavily", "web search fallback", "https://app.tavily.com", _tavily),
    ("SERP_API_KEY", "SerpAPI", "Google results, last search fallback", "https://serpapi.com/manage-api-key", _serpapi),
]


def read_env(path: Path) -> dict[str, str]:
    values = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and not name.lstrip().startswith("#"):
                values[name.strip()] = value.strip().strip('"')
    return values


def write_env(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    remaining = dict(updates)
    out = []
    for line in lines:
        name = line.partition("=")[0].strip()
        if name in remaining:
            value = remaining.pop(name)
            if value:
                out.append(f"{name}={value}")
        else:
            out.append(line)
    out += [f"{name}={value}" for name, value in remaining.items() if value]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)


def check(value: str, probe) -> tuple[bool, str]:
    try:
        return True, probe(value)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def run_check() -> None:
    for name, label, purpose, _, probe in KEYS:
        value = os.environ.get(name, "")
        if not value:
            print(f"  -  {label:<12} not set ({purpose} disabled)")
            continue
        ok, detail = check(value, probe)
        print(f"  {'OK' if ok else '!!'} {label:<12} {detail}")


def run_setup(browser: bool = True) -> None:
    if not sys.stdin.isatty():
        sys.exit("scrappy setup is interactive; in non-interactive environments set the keys as environment variables.")
    saved = read_env(ENV_FILE)
    print(f"scrappy setup: keys are saved to {ENV_FILE}\n"
          "Each key turns on one source. Press Enter to skip a key (or keep the one already saved).\n"
          "Static pages, crawling and YouTube work without any key.\n")
    updates = {}
    for name, label, purpose, url, probe in KEYS:
        current = saved.get(name) or os.environ.get(name, "")
        print(f"{label}: {purpose}\n  get a key: {url}")
        entered = getpass(f"  {name} [{'Enter keeps current' if current else 'Enter skips'}]: ").strip()
        value = entered or current
        if value:
            ok, detail = check(value, probe)
            print(f"  {'OK' if ok else 'FAILED'}: {detail}")
            if not ok and entered and input("  save it anyway? [y/N] ").strip().lower() != "y":
                value = current
        updates[name] = value
        print()
    write_env(ENV_FILE, updates)
    enabled = [label for name, label, *_ in KEYS if updates.get(name)]
    print(f"Saved {ENV_FILE}. Enabled: {', '.join(enabled) or 'free sources only'}.")
    if browser and input("\nDownload the stealth browser for JavaScript-heavy pages (a few hundred MB)? [Y/n] ").strip().lower() != "n":
        from scrapling.cli import install

        install([], standalone_mode=False)
