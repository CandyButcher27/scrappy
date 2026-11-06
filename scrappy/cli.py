import argparse
import json
import sys

from . import agent


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="scrappy", description="Fetch a URL or search the web; prints JSON.")
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch", help="fetch a URL through the cheapest method that works")
    f.add_argument("url")
    f.add_argument("--expect", help="text that must appear in the result, else try the next method")
    f.add_argument("--via", choices=sorted(agent.METHODS), help="use only this page method")
    s = sub.add_parser("search", help="search the web")
    s.add_argument("query")
    s.add_argument("-n", type=int, default=5)
    args = parser.parse_args()

    if args.command == "fetch":
        result, attempts = agent.fetch(args.url, args.expect, args.via)
        out = {"ok": result is not None, "url": args.url, "attempts": attempts}
        if result:
            out |= {"method": result.method, "title": result.title, "status": result.status, "text": result.text, "data": result.data}
    else:
        method, results, attempts = agent.search(args.query, args.n)
        out = {"ok": method is not None, "query": args.query, "method": method, "results": results, "attempts": attempts}
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    sys.exit(0 if out["ok"] else 1)
