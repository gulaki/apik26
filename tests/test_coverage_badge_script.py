"""`.github/scripts/coverage_badge.py`: turns coverage.py's JSON report into
the shields.io endpoint data behind the README's coverage badge, published
with the HTML report on GitHub Pages by the coverage workflow."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".github" / "scripts" / "coverage_badge.py"


def load():
    spec = importlib.util.spec_from_file_location("coverage_badge", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("percent, message, color", [
    (97.83, "97%", "brightgreen"),
    (95.0, "95%", "brightgreen"),
    (94.99, "94%", "green"),
    (85.0, "85%", "yellowgreen"),
    (72.0, "72%", "yellow"),
    (50.0, "50%", "red"),
    (100.0, "100%", "brightgreen"),
])
def test_the_badge_shows_the_percentage_rounded_down(percent, message, color):
    assert load().badge(percent) == {"schemaVersion": 1, "label": "coverage", "message": message, "color": color}


def test_the_command_line_reads_coverage_json(tmp_path):
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"totals": {"percent_covered": 96.4}}), encoding="utf-8")
    out = tmp_path / "badge.json"
    run = subprocess.run([sys.executable, str(SCRIPT), str(report), str(out)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["message"] == "96%"


def test_the_threshold_is_a_whole_number():
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["coverage"]
    assert config["run"]["source"] == ["apik26"] and config["run"]["branch"] is True
    assert isinstance(config["report"]["fail_under"], int)
