"""Tests that need a tool skip without it, except where APIK_REQUIRE names
that tool: CI lists the tools each job installs, and there a missing one
fails the test, so a green run never means a smaller run."""
import sys
from pathlib import Path

import pytest

import conftest


def test_a_missing_tool_skips_by_default(monkeypatch):
    monkeypatch.delenv("APIK_REQUIRE", raising=False)
    with pytest.raises(pytest.skip.Exception, match="make not installed"):
        conftest.missing("make", "make not installed")


def test_a_missing_required_tool_fails(monkeypatch):
    monkeypatch.setenv("APIK_REQUIRE", "cc, make")
    with pytest.raises(pytest.fail.Exception, match="APIK_REQUIRE"):
        conftest.missing("make", "make not installed")
    with pytest.raises(pytest.skip.Exception):
        conftest.missing("node", "node not installed")


def test_an_unknown_tool_name_is_a_usage_error(monkeypatch):
    monkeypatch.setenv("APIK_REQUIRE", "cc,gcc")
    with pytest.raises(pytest.UsageError, match="gcc"):
        conftest.required_tools()


def test_cc_chooses_the_c_compiler():
    assert conftest.find_c_compiler({"CC": sys.executable}) == sys.executable
    assert conftest.find_c_compiler({"CC": "no-such-compiler-apik26"}) is None


def test_every_skip_goes_through_missing():
    """A bare pytest.skip would skip even where APIK_REQUIRE names the tool."""
    tests = Path(__file__).resolve().parent
    bare = [f"{path.name}:{number}"
            for path in sorted(tests.glob("*.py")) if path.name not in ("conftest.py", "test_require.py")
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if "pytest.skip(" in line]
    assert bare == []
