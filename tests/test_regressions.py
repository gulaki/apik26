"""Regression tests for bugs found in review. Each section names the bug.

End-to-end tests build the generated C with strict flags (see conftest.py) and
check what the program actually prints, because most of these bugs only show
up once a real C compiler gets involved.
"""
import pytest

from apik26.build import BUILD_SYSTEMS, BuildConfig
from apik26.cli import main
from apik26.diagnostics import Diagnostics
from apik26.errors import ParseError
from apik26.parser import Parser


def c_source(compiler, source):
    return compiler.compile(source).c_source


# -- Bug 1: number literals were emitted as C `int` literals ----------------
# `7` was emitted as the C int `7`, so arithmetic on literals used C `int`
# rules and could overflow, which is undefined. Literals now get an APIK26 type
# (i64 or f64, see docs/design/type-system.md) and integer constant
# expressions are folded exactly, so C never does arithmetic on a bare literal.

def test_division_of_float_literals_is_float_division(run_apik):
    assert run_apik("print 7.0 / 2\n") == "3.50\n"


def test_literal_division_by_zero_is_rejected_not_undefined(compiler, run_apik):
    assert [d.code.code for d in compiler.compile("print 1 // 0\n").diagnostics] == ["E0504"]
    assert run_apik("print 1.0 / 0\n") == "inf\n"
    assert run_apik("print 1 / 0\n") == "inf\n"  # `/` divides floats


def test_literal_multiplication_does_not_overflow_int(run_apik):
    assert run_apik("print 65536 * 65536\n") == "4294967296\n"


def test_literal_wider_than_any_c_integer(compiler, run_apik):
    assert [d.code.code for d in compiler.compile("print 99999999999999999999\n").diagnostics] == ["E0401"]
    assert run_apik("print 99999999999999999999.0\n") == "100000000000000000000.00\n"


def test_comparison_of_literals_uses_their_values(run_apik):
    assert run_apik('if 7.0 / 2 == 3 {\n    print "int"\n} else {\n    print "float"\n}\n') == "float\n"
    assert run_apik('if 7 / 2 == 3 {\n    print "int"\n} else {\n    print "float"\n}\n') == "float\n"
    assert run_apik('if 7 // 2 == 3 {\n    print "int"\n} else {\n    print "float"\n}\n') == "int\n"


@pytest.mark.parametrize("literal, expected", [("7", "INT64_C(7)"), ("0", "INT64_C(0)"), ("2.5", "2.5"), ("2.5f", "2.5f")])
def test_number_literals_are_emitted_with_their_c_type(compiler, literal, expected):
    assert f"v_x = {expected};" in c_source(compiler, f"x = {literal}\n")


def test_literal_too_large_for_a_float_is_rejected(compiler):
    result = compiler.compile("x = 1e39f\n")
    assert [d.code.code for d in result.diagnostics] == ["E0401"]
    assert "does not fit in f32" in result.diagnostics[0].message


def test_largest_float_literal_is_accepted(compiler):
    assert compiler.compile("x = 340282346638528859811704183484516925440.0f\n").ok


# -- Bug 2: string `print` used the text as a printf format string ----------

def test_percent_signs_in_strings_are_printed_literally(run_apik):
    assert run_apik('print "100% done %s %n %d"\n') == "100% done %s %n %d\n"


def test_string_print_does_not_go_through_printf(compiler):
    source = c_source(compiler, 'print "50%"\n')
    assert 'puts("50%");' in source
    assert 'printf("50%' not in source


# -- Bug 3: non-ASCII string text was double-encoded ------------------------
# `unicode_escape` decodes the UTF-8 bytes as Latin-1, so "é" became "Ã©".

def test_non_ascii_strings_round_trip(run_apik):
    assert run_apik('print "héllo ✓ 日本"\n') == "héllo ✓ 日本\n"


def test_non_ascii_string_is_decoded_once():
    stmt = Parser().parse('print "é"\n').statements[0]
    assert stmt.value == "é"


def test_non_ascii_text_is_emitted_as_escapes(compiler):
    # Plain ASCII C source cannot be misread under a different source charset.
    source = c_source(compiler, 'print "é"\n')
    assert 'puts("\\303\\251");' in source
    assert source.isascii()


# -- Bug 4: `\r` escapes and `??` sequences broke the C string literal ------

def test_carriage_return_and_tab_escapes(compiler, run_apik):
    # A raw carriage return inside a C string literal ended the line, so the
    # C did not compile. (run_apik reads stdout in text mode, which turns
    # the `\r` into `\n`, hence the C-level check too.)
    program = 'print "a\\rb\\tc"\n'
    assert 'puts("a\\rb\\tc");' in c_source(compiler, program)
    assert run_apik(program) == "a\nb\tc\n"


def test_trigraph_like_text_is_printed_unchanged(run_apik):
    # Under -std=c11 a C compiler replaces `??/` with `\`.
    assert run_apik('print "what??/ ??= ??!"\n') == "what??/ ??= ??!\n"


@pytest.mark.parametrize("escape, expected", [
    ('\\"', '"'), ("\\\\", "\\"), ("\\n", "\n"), ("\\r", "\r"), ("\\t", "\t"),
])
def test_every_string_escape_decodes(escape, expected):
    assert Parser().parse(f'print "{escape}"\n').statements[0].value == expected


def test_escaped_backslash_followed_by_n_is_not_a_newline(run_apik):
    assert run_apik('print "a\\\\nb"\n') == "a\\nb\n"


# -- Bug 5: APIK26 names collided with C keywords and <stdio.h> names -------
# Names were emitted verbatim, so `int = 1` declared `float int;`.

@pytest.mark.parametrize("name", [
    "int", "float", "return", "main", "printf", "puts", "scanf", "stdin",
    "EOF", "NULL", "FILE", "__x", "_X",
])
def test_variables_named_like_c_identifiers_work(run_apik, name):
    assert run_apik(f"{name} = 3\nprint {name} + 1\n") == "4\n"


@pytest.mark.parametrize("name", ["EOF", "int", "main", "BUFSIZ", "L_tmpnam"])
def test_labels_named_like_c_identifiers_work(run_apik, name):
    program = f'goto {name}\nprint "skipped"\nlabel {name}\nprint "after"\n'
    assert run_apik(program) == "after\n"


def test_block_variable_named_like_a_c_identifier_works(run_apik):
    assert run_apik("{\n    short = 2.0\n    input double\n    print short * double\n}\n", "5\n") == "10.00\n"


def test_variable_and_label_with_the_same_name(run_apik):
    program = "x = 0\nlabel x\nx = x + 1\nif x < 3 {\n    goto x\n}\nprint x\n"
    assert run_apik(program) == "3\n"


# -- Bug 6: build files pointed at the wrong paths --------------------------

def test_cli_writes_the_build_file_next_to_the_c_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "prog.apik"
    src.write_text("print 1\n", encoding="utf-8")
    (tmp_path / "out").mkdir()
    assert main([str(src), "-o", "out/prog.c", "--build", "make"]) == 0
    assert (tmp_path / "out" / "Makefile").exists()
    assert not (tmp_path / "Makefile").exists()


@pytest.mark.parametrize("system", ["make", "ninja"])
def test_build_file_paths_are_relative_to_the_build_file(tmp_path, system):
    build_file = tmp_path / "build" / "rules"
    text = BUILD_SYSTEMS[system].generate(
        tmp_path / "gen" / "prog.c", tmp_path / "bin" / "prog", build_file, BuildConfig()
    )
    assert "../gen/prog.c" in text
    assert "../bin/prog" in text


def test_generated_makefile_builds_the_program(tmp_path, run_apik):
    # run_apik is only requested so the test skips without a C compiler.
    import subprocess

    from conftest import require_tool

    require_tool("make")
    src = tmp_path / "prog.apik"
    src.write_text('print "built"\n', encoding="utf-8")
    out = tmp_path / "gen" / "prog.c"
    out.parent.mkdir()
    build_file = tmp_path / "build" / "Makefile"
    build_file.parent.mkdir()
    assert main([str(src), "-o", str(out), "--build", "make", "--build-output", str(build_file)]) == 0
    subprocess.run(["make", "-C", str(build_file.parent)], check=True, capture_output=True)
    run = subprocess.run([str(tmp_path / "gen" / "prog")], capture_output=True, text=True)
    assert run.stdout == "built\n"


# -- Bug 7: AST locations were lost for parenthesised expressions -----------

def test_grouped_expression_has_a_location():
    stmt = Parser().parse("x = (1) + 2\n").statements[0]
    assert stmt.value.location.line == 1
    assert stmt.value.left.location.line == 1


# -- Bug 8: parse error messages --------------------------------------------

def test_parse_error_without_filename_reads_cleanly():
    with pytest.raises(ParseError) as info:
        Parser().parse("x = \n")
    assert str(info.value).startswith("<input>:1:5: error[E0101]: ")


def test_parse_error_with_filename():
    diags = Diagnostics("f.apik")
    Parser().parse("x = \n", diags)
    assert [(x.span.filename, x.span.line, x.span.column) for x in diags] == [("f.apik", 1, 5)]


def test_parse_error_at_end_of_input_names_it():
    with pytest.raises(ParseError) as info:
        Parser().parse("if 1 > 0 {")
    assert "missing '}'" in str(info.value)
    assert "$END" not in str(info.value)


# -- Bug 9: `input` used scanf("%f"), which is undefined for out-of-range text --

READ_AND_PRINT = "input a\ninput b\nprint a\nprint b\n"


@pytest.mark.parametrize("stdin, expected", [
    ("1.5\n2\n", "1.50\n2.00\n"),
    ("  7   \n\n 8\n", "7.00\n8.00\n"),               # any whitespace separates tokens
    ("1e999\n3\n", "0.00\n3.00\n"),                     # out of range: was undefined
    ("-1e999\n3\n", "0.00\n3.00\n"),
    ("nan\n3\n", "0.00\n3.00\n"),                       # non-finite is not an APIK26 number
    ("inf\n3\n", "0.00\n3.00\n"),
    ("abc\n4\n", "0.00\n4.00\n"),                       # bad token consumed, next one read
    ("12abc\n4\n", "0.00\n4.00\n"),                     # trailing junk rejects the whole token
    ("9" * 200 + "\n5\n", "0.00\n5.00\n"),              # over-long token consumed entirely
    ("", "0.00\n0.00\n"),                               # end of input
    ("6", "6.00\n0.00\n"),                              # no trailing newline
])
def test_input_never_misreads_or_overflows(run_apik, stdin, expected):
    assert run_apik(READ_AND_PRINT, stdin) == expected


def test_input_helper_only_emitted_when_used(compiler):
    assert "apik_read" not in c_source(compiler, "print 1\n")
    assert "scanf" not in c_source(compiler, "input x\n")


# -- Bug 10: comparisons were wrapped in a second pair of parentheses --------
# `if ((a == b))` makes clang warn (-Wparentheses-equality).

def test_conditions_have_a_single_pair_of_parentheses(compiler):
    source = c_source(compiler, "x = 1\nif x == 1 {\n    print x\n}\nwhile x < 3 {\n    x = x + 1\n}\n")
    assert "if (v_x == INT64_C(1)) {" in source
    assert "while (v_x < INT64_C(3)) {" in source
    assert "((" not in source[source.index("int main"):]


def test_generated_c_builds_without_any_warning(compiler, tmp_path):
    import subprocess

    from conftest import EXAMPLES, require_cc

    C_COMPILER = require_cc()
    for example in sorted(EXAMPLES.glob("*.apik")):
        c_file = tmp_path / f"{example.stem}.c"
        result = compiler.compile(example.read_text(encoding="utf-8"))
        c_file.write_text(result.c_source, encoding="utf-8")
        build = subprocess.run(
            [C_COMPILER, "-std=c11", "-pedantic-errors", "-Wall", "-Wextra", "-Werror",
             "-o", str(tmp_path / example.stem), str(c_file), *(f"-l{lib}" for lib in result.link_libraries)],
            capture_output=True, text=True,
        )
        assert build.returncode == 0, f"{example.name}: {build.stderr}"


# -- Bug 11: huge number literals crashed or hung the compiler ---------------
# Python's int() refuses more than 4300 decimal digits, and Fraction("1e1000000000")
# builds a billion-digit integer. Each case runs in a fresh process, so a hang
# fails on the timeout instead of stopping the test run.

def _compile_in_process(tmp_path, source):
    import subprocess
    import sys

    src = tmp_path / "big.apik"
    src.write_text(source, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "apik26.cli", str(src), "-o", str(tmp_path / "big.c")],
        capture_output=True, text=True, timeout=60,
    )


@pytest.mark.parametrize("source, code", [
    ("x = " + "9" * 5000 + "\n", "E0401"),
    ("x = 0x" + "f" * 5000 + "\n", "E0401"),
    ("x = 1e1000000000\n", "E0401"),
    ("x = 1e" + "0" * 5000 + "999\n", "E0401"),
    ("x = (2 ** 16000) ** 2\n", "E0503"),
    ("x = " + " * ".join(["(2 ** 16000)"] * 40) + "\n", "E0503"),
])
def test_a_huge_constant_is_an_error_not_a_crash(tmp_path, source, code):
    run = _compile_in_process(tmp_path, source)
    assert run.returncode == 1, run.stderr
    assert f"error[{code}]" in run.stderr
    assert len(run.stderr) < 2000, "the message should not spell out the whole number"


@pytest.mark.parametrize("source", [
    "x = 1e-1000000000\nprint x\n",
    "x = 0." + "0" * 5000 + "1\nprint x\n",
    "x = 1." + "3" * 5000 + "\nprint x\n",
])
def test_a_long_or_tiny_float_literal_compiles(tmp_path, source):
    run = _compile_in_process(tmp_path, source)
    assert run.returncode == 0, run.stderr


def test_a_long_float_literal_rounds_once(run_apik):
    assert run_apik("x = 1." + "3" * 5000 + "\nprint x\n") == "1.33\n"
    assert run_apik("x = 1e-1000000000\nprint x\n") == "0.00\n"


def test_a_constant_too_large_for_every_type_says_so(compiler):
    # Folding stops once no type can hold the value: 2 ** 32000 here.
    result = compiler.compile("x = 2 ** 16000 * 2 ** 16000 // 2 ** 31999\n")
    assert [d.message for d in result.errors] == [
        "constant expression 9.1172e+9632 does not fit in any type"]


def test_a_long_number_in_a_message_is_shortened(compiler):
    (error,) = compiler.compile("print 2 ** 1000\n").errors
    assert error.message == "constant expression 1.0715e+301 does not fit in i64"
    (error,) = compiler.compile("print 9223372036854775807 + 1\n").errors
    assert error.message == "constant expression 9223372036854775808 does not fit in i64"


# -- Bug 12: a runtime error lost or reordered the output before it ----------
# abort() need not flush stdout (glibc's does not), and stdout is buffered
# when it is not a terminal.

def test_output_before_a_runtime_error_is_kept(build_apik):
    from conftest import extra_flags

    proc = build_apik("print 1\nx = 9223372036854775807\nx = x + 1\n", extra_flags())("")
    assert proc.returncode != 0
    assert proc.stdout == "1\n"


def test_output_before_a_runtime_error_comes_first(compiler, tmp_path):
    import os
    import subprocess

    from conftest import STRICT_FLAGS, require_cc

    result = compiler.compile("print 1\nx = 9223372036854775807\nx = x + 1\n", "t.apik")
    c_file = tmp_path / "prog.c"
    c_file.write_text(result.c_source, encoding="utf-8")
    exe = tmp_path / ("prog.exe" if os.name == "nt" else "prog")
    subprocess.run([require_cc(), *STRICT_FLAGS, "-o", str(exe), str(c_file)], check=True)
    # One pipe for both streams, so the order is the order they were written.
    proc = subprocess.run([str(exe)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
    # Windows' abort() may add a line of its own after ours.
    assert proc.stdout.splitlines()[:2] == ["1", "t.apik:3:7: runtime error: integer overflow"]


# -- Bug 13: a NaN printed as "-nan" on some platforms -----------------------
# x86 makes inf - inf a NaN with the sign bit set, and glibc, musl (wasm) and
# Windows print that as "-nan" or "-nan(ind)".

@pytest.mark.parametrize("program", [
    "x = 1.0 / 0.0\nprint x - x\n",
    "x = 1.0 / 0.0\nprint 0.0 * x\n",
    "y = 0.0\nprint -(y / y)\n",
    "x = 1.0f / 0.0f\nprint x - x\n",
])
def test_every_nan_prints_as_nan(run_apik, program):
    assert run_apik(program) == "nan\n"


# -- Bug 14: `-o prog --build make` built the C file over itself ------------
# The executable is the C file's name without its suffix, so with no suffix
# the Makefile's rule was `prog: prog`.

def test_build_needs_a_c_file_with_a_suffix(tmp_path, capsys):
    src = tmp_path / "p.apik"
    src.write_text("print 1\n", encoding="utf-8")
    with pytest.raises(SystemExit) as info:
        main([str(src), "-o", str(tmp_path / "prog"), "--build", "make"])
    assert info.value.code == 2
    assert "--build needs a C file name with a suffix" in capsys.readouterr().err
    assert not (tmp_path / "prog").exists()


# -- Bug 15: a UTF-8 byte order mark was an unexpected character ------------
# Windows editors such as Notepad can start a UTF-8 file with one.

def test_a_byte_order_mark_is_ignored(tmp_path):
    src = tmp_path / "bom.apik"
    src.write_bytes(b"\xef\xbb\xbfprint 1\n")
    out = tmp_path / "bom.c"
    assert main([str(src), "-o", str(out)]) == 0
    assert "puts" in out.read_text(encoding="utf-8") or "printf" in out.read_text(encoding="utf-8")
