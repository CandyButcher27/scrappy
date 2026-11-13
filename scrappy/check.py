from dataclasses import dataclass, field

BLOCK_PHRASES = (
    "you have been blocked",
    "attention required! | cloudflare",
    "just a moment...",
    "performing security verification",
    "blocked by network security",
    "enable javascript and cookies to continue",
    "verify you are human",
    "access denied",
)
MIN_TEXT = 200


@dataclass
class Result:
    url: str
    method: str
    title: str | None = None
    text: str = ""
    status: int | None = None
    data: dict | list | None = field(default=None, repr=False)


def problem(result: Result, expect: str | None = None) -> str | None:
    if result.status and result.status >= 400:
        return f"http {result.status}"
    if result.data:
        return None
    lowered = result.text.lower()
    for phrase in BLOCK_PHRASES:
        if phrase in lowered[:5000]:
            return f"block page ({phrase!r})"
    if expect and expect.lower() not in lowered:
        return f"expected text {expect!r} not found"
    if len(result.text.strip()) < MIN_TEXT:
        return f"too little text ({len(result.text.strip())} chars)"
    return None
