"""Write the shields.io endpoint data for the coverage badge.

  coverage_badge.py coverage.json badge.json

The percentage is rounded down, like coverage.py's fail_under check, so the
badge never shows more than was measured."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

COLORS = ((95, "brightgreen"), (90, "green"), (80, "yellowgreen"), (70, "yellow"))


def badge(percent: float) -> dict:
    whole = math.floor(percent)
    color = next((name for limit, name in COLORS if whole >= limit), "red")
    return {"schemaVersion": 1, "label": "coverage", "message": f"{whole}%", "color": color}


if __name__ == "__main__":
    report, out = Path(sys.argv[1]), Path(sys.argv[2])
    percent = json.loads(report.read_text(encoding="utf-8"))["totals"]["percent_covered"]
    out.write_text(json.dumps(badge(percent)) + "\n", encoding="utf-8")
