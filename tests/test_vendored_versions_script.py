"""`.github/scripts/vendored_versions.py`: the weekly workflow's report of
newer npm releases of the web shell's vendored libraries. It only reports:
xterm-pty needs xterm 5, so a newer xterm is not always an upgrade."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / ".github" / "scripts" / "vendored_versions.py"


def load():
    spec = importlib.util.spec_from_file_location("vendored_versions", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LIBRARIES = [{"name": "@xterm/xterm", "version": "5.5.0"}, {"name": "xterm-pty", "version": "0.12.0"}]


def test_the_report_lists_every_library_and_flags_newer_ones():
    report = load().report(LIBRARIES, {"@xterm/xterm": "6.0.0", "xterm-pty": "0.12.0"})
    assert report.splitlines() == [
        "| Library | Vendored | Latest on npm |",
        "|---|---|---|",
        "| @xterm/xterm | 5.5.0 | **6.0.0** |",
        "| xterm-pty | 0.12.0 | 0.12.0 |",
    ]


def test_an_unreachable_registry_is_reported_not_raised():
    report = load().report(LIBRARIES, {"@xterm/xterm": None, "xterm-pty": "0.12.0"})
    assert "| @xterm/xterm | 5.5.0 | unknown |" in report


def test_the_manifest_is_read():
    names = [library["name"] for library in load().libraries()]
    assert names == ["@xterm/xterm", "@xterm/addon-fit", "xterm-pty"]
