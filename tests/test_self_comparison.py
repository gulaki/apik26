"""Comparing an integer or bool with itself (`a == a`, `a < a`) is valid
APIK26, but gcc and clang warn that the C comparison is always true or
false (-Wtautological-compare). The generated C must build without
warnings, so the statement that holds such a comparison, and only that one,
is wrapped in `#pragma GCC diagnostic` lines (docs/design/lowering.md,
"Self-comparisons"). A float compared with itself is a NaN test, and C
compilers do not warn about it."""
import pytest

PUSH = "#pragma GCC diagnostic push"
IGNORE = '#pragma GCC diagnostic ignored "-Wtautological-compare"'
POP = "#pragma GCC diagnostic pop"


def pragma_lines(c_source):
    return [line.strip() for line in c_source.splitlines() if line.strip().startswith("#pragma")]


@pytest.mark.parametrize("source", [
    "a = 1\nprint a == a\n",
    "a = 1\nprint a < a\n",
    "p = true\nprint p != p\n",
    "a = 1\nb = 2\nprint a < a < b\n",
    "a = 1\nif a >= a {\n    print 1\n}\n",
    "a = 1\nwhile a > a {\n    a = 2\n}\n",
    "a = 1\nprint (a) == a\n",
])
def test_the_statement_with_a_self_comparison_is_wrapped(compiler, source):
    c = compiler.compile(source).c_source
    lines = [line.strip() for line in c.splitlines()]
    assert pragma_lines(c) == [PUSH, IGNORE, POP]
    start = lines.index(PUSH)
    assert lines[start + 1] == IGNORE and lines[start + 3] == POP  # exactly one statement inside


@pytest.mark.parametrize("source", [
    "a = 1\nb = 2\nprint a == b\n",
    "x = 1.0\nprint x == x\n",
    "a = 1\nprint a + 1 == a + 1\n",
])
def test_other_comparisons_are_not_wrapped(compiler, source):
    assert pragma_lines(compiler.compile(source).c_source) == []


def test_only_the_statements_that_need_it_are_wrapped(compiler):
    c = compiler.compile("a = 1\nb = 2\nprint a == b\nprint a == a\nprint b < a\nprint b == b\n").c_source
    assert pragma_lines(c).count(PUSH) == 2


@pytest.mark.parametrize("source, output", [
    ("a = 1\nprint a == a\nprint a < a\n", "true\nfalse\n"),
    ("p = false\nprint p == p\nprint p != p\n", "true\nfalse\n"),
    ("a = 1\nb = 2\nprint a <= a < b\n", "true\n"),
    ("a = 1\nif a == a {\n    print 7\n}\n", "7\n"),
])
def test_self_comparisons_build_without_warnings_and_run(build_apik, source, output):
    proc = build_apik(source, ["-Werror"])("")
    assert (proc.returncode, proc.stdout) == (0, output), proc.stderr
