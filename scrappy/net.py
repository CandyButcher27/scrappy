import json
import os
import urllib.request
from pathlib import Path

ENV_FILES = [Path.cwd() / ".env", Path.home() / ".scrappy" / ".env"]

for env_file in ENV_FILES:
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and not name.lstrip().startswith("#"):
                os.environ.setdefault(name.strip(), value.strip().strip('"'))


def key(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is not set (environment, ./.env or ~/.scrappy/.env)")
    return value


def request(url: str, body=None, headers=None, timeout: float = 120):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", "User-Agent": "scrappy/0.2", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers, r.read()


def request_json(url: str, body=None, headers=None, timeout: float = 120):
    return json.loads(request(url, body, headers, timeout)[2])
