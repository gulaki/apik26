"""Print a Markdown table of the web shell's vendored libraries
(scribe_lang/web/assets.json) next to their latest npm releases.

It reports and never fails: xterm-pty needs xterm 5, so a newer release is a
prompt to look, not always an upgrade."""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[2] / "scribe_lang" / "web" / "assets.json"


def libraries() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["libraries"]


def latest(name: str) -> str | None:
    url = f"https://registry.npmjs.org/{urllib.parse.quote(name, safe='@')}/latest"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response)["version"]
    except (OSError, ValueError, KeyError):
        return None


def report(libraries: list[dict], versions: dict[str, str | None]) -> str:
    lines = ["| Library | Vendored | Latest on npm |", "|---|---|---|"]
    for library in libraries:
        newest = versions[library["name"]]
        shown = "unknown" if newest is None else newest if newest == library["version"] else f"**{newest}**"
        lines.append(f"| {library['name']} | {library['version']} | {shown} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    found = libraries()
    sys.stdout.write(report(found, {library["name"]: latest(library["name"]) for library in found}))
