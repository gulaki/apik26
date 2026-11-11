"""Read CHANGELOG.md for the workflows.

  changelog.py check BASE HEAD     exit 1 unless HEAD's "Unreleased" section
                                   has entries BASE's lacks (pull request check)
  changelog.py notes X.Y.Z         print that release's section (release notes);
                                   --link-base URL makes relative links absolute
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HEADING = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
RELATIVE_LINK = re.compile(r"\]\((?![a-z]+:|#)([^)\s]+)\)")


def sections(text: str) -> dict[str, str]:
    """Each `## ` heading's text -> the section under it, without blank edges."""
    found = {}
    matches = list(HEADING.finditer(text))
    for match, following in zip(matches, matches[1:] + [None]):
        end = following.start() if following else len(text)
        found[match.group(1)] = text[match.end():end].strip("\n") + "\n"
    return found


def notes(text: str, version: str, link_base: str | None = None) -> str:
    """That release's section. With `link_base`, links to files in the
    repository become links under it (the release page is not in the repo)."""
    for heading, body in sections(text).items():
        if heading.split(" - ")[0] == version:
            return body if link_base is None else RELATIVE_LINK.sub(lambda m: f"]({link_base}{m.group(1)})", body)
    raise LookupError(f"CHANGELOG.md has no section for {version}")


def new_entries(base: str, head: str) -> list[str]:
    """The list items in head's Unreleased section that base's lacks."""
    def entries(text: str) -> list[str]:
        body = sections(text).get("Unreleased", "")
        return [line for line in body.splitlines() if line.startswith("- ")]

    old = set(entries(base))
    return [line for line in entries(head) if line not in old]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("base", type=Path)
    check.add_argument("head", type=Path)
    release = commands.add_parser("notes")
    release.add_argument("version")
    release.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    release.add_argument("--link-base")
    args = parser.parse_args(argv)

    if args.command == "check":
        added = new_entries(args.base.read_text(encoding="utf-8"), args.head.read_text(encoding="utf-8"))
        if not added:
            print('This pull request changes apik26/ but adds no entry under "Unreleased" in '
                  "CHANGELOG.md. Add one, or add the no-changelog label if users will not notice the change.")
            return 1
        print("New changelog entries:", *added, sep="\n")
        return 0
    try:
        sys.stdout.write(notes(args.changelog.read_text(encoding="utf-8"), args.version, args.link_base))
    except LookupError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
