import argparse
import json
import sys
from importlib.metadata import version

from . import agent
from .platforms import SEARCHABLE


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="scrappy", description="Fetch, search and crawl the web and social platforms; prints JSON.")
    parser.add_argument("--version", action="version", version=f"scrappy {version('scrappy-agent')}")
    sub = parser.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fetch", help="fetch a URL through the cheapest source that works")
    f.add_argument("url")
    f.add_argument("--expect", help="text that must appear in the result, else try the next source")
    f.add_argument("--via", choices=sorted(agent.METHODS), help="use only this page method")
    f.add_argument("--limit", type=int, default=20, help="max posts or comments for social URLs (default 20)")

    s = sub.add_parser("search", help="search the web, or a social platform with --on")
    s.add_argument("query")
    s.add_argument("-n", type=int, default=5)
    s.add_argument("--on", choices=SEARCHABLE, help="search this platform instead of the web")

    c = sub.add_parser("crawl", help="follow links within one site")
    c.add_argument("url")
    c.add_argument("--limit", type=int, default=20, help="max pages (default 20)")
    c.add_argument("--depth", type=int, default=2, help="max link depth from the start URL (default 2)")
    c.add_argument("--expect", help="text the start page must contain")
    c.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1)")

    sub.add_parser("mcp", help="run as an MCP server over stdio")
    st = sub.add_parser("setup", help="enter API keys and download the stealth browser")
    st.add_argument("--check", action="store_true", help="only test the keys already configured")
    st.add_argument("--no-browser", action="store_true", help="skip the browser download")
    args = parser.parse_args()

    if args.command == "mcp":
        from .mcp_server import main as serve

        return serve()
    if args.command == "setup":
        from .setup import run_check, run_setup

        return run_check() if args.check else run_setup(browser=not args.no_browser)

    if args.command == "fetch":
        out = agent.run_fetch(args.url, args.expect, args.via, args.limit)
    elif args.command == "search":
        out = agent.run_search(args.query, args.n, args.on)
    else:
        out = agent.run_crawl(args.url, args.limit, args.depth, args.expect, args.delay)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    sys.exit(0 if out["ok"] else 1)
