"""`.github/scripts/changelog.py`, used by two workflows: the pull request
check that compiler changes come with an "Unreleased" entry, and the release
workflow that turns a version's section into its GitHub Release notes."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".github" / "scripts" / "changelog.py"


def load():
    spec = importlib.util.spec_from_file_location("changelog", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHANGELOG = """# Changelog

Intro.

## Versioning

Rules.

## Unreleased

### Added

- Float `//`.

## 0.6.2 - 2026-10-30

Pull request #12.

### Added

- Something.

## 0.6.1 - 2026-10-30

Pull request #11.
"""


def test_the_notes_of_a_release_are_its_section():
    assert load().notes(CHANGELOG, "0.6.2") == "Pull request #12.\n\n### Added\n\n- Something.\n"
    assert load().notes(CHANGELOG, "0.6.1") == "Pull request #11.\n"


def test_relative_links_can_point_at_the_release():
    text = "## 1.0.0 - 2026-11-01\n\nSee [errors](docs/errors.md#codes), [web](https://x.org) and [here](#top).\n"
    assert load().notes(text, "1.0.0", link_base="https://github.com/o/r/blob/v1.0.0/") == (
        "See [errors](https://github.com/o/r/blob/v1.0.0/docs/errors.md#codes), [web](https://x.org) and [here](#top).\n"
    )


def test_a_missing_release_is_an_error():
    with pytest.raises(LookupError, match="0.9.9"):
        load().notes(CHANGELOG, "0.9.9")


def test_new_entries_are_the_unreleased_lines_the_base_lacks():
    base = CHANGELOG.replace("- Float `//`.\n", "")
    assert load().new_entries(base, CHANGELOG) == ["- Float `//`."]
    assert load().new_entries(CHANGELOG, CHANGELOG) == []
    released = CHANGELOG.replace("## Unreleased\n\n### Added\n\n- Float `//`.\n\n", "")
    assert load().new_entries(released, released) == []


def test_every_real_release_has_notes():
    module = load()
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    assert module.notes(text, version).strip()


def test_the_command_line(tmp_path):
    base, head = tmp_path / "base.md", tmp_path / "head.md"
    base.write_text(CHANGELOG.replace("- Float `//`.\n", ""), encoding="utf-8")
    head.write_text(CHANGELOG, encoding="utf-8")

    def run(*args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    assert run("check", str(base), str(head)).returncode == 0
    missing = run("check", str(head), str(head))
    assert missing.returncode == 1 and "Unreleased" in missing.stdout
    notes = run("notes", "0.6.1", "--changelog", str(head))
    assert (notes.returncode, notes.stdout) == (0, "Pull request #11.\n")
