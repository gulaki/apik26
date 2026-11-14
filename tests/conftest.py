from __future__ import annotations

import functools
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from typing import NoReturn

import pytest

from apik26.compiler import Compiler

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

# The tools a test may need. Without one the test skips, unless
# APIK_REQUIRE (a comma-separated list of these names) includes it: CI
# names the tools each job installs, and there a missing tool fails the test,
# so a green run never means a smaller run.
TOOLS = ("cc", "ubsan", "make", "node", "emcc")


def required_tools() -> set[str]:
    required = {name.strip() for name in os.environ.get("APIK_REQUIRE", "").split(",") if name.strip()}
    unknown = required - set(TOOLS)
    if unknown:
        raise pytest.UsageError(f"APIK_REQUIRE: unknown tools {sorted(unknown)}; the tools are {', '.join(TOOLS)}")
    return required


def missing(tool: str, reason: str) -> NoReturn:
    """Skip the test for lack of `tool`, or fail it if APIK_REQUIRE names it."""
    if tool in required_tools():
        pytest.fail(f"{reason}, but APIK_REQUIRE lists {tool}", pytrace=False)
    pytest.skip(reason)


def require_tool(name: str) -> str:
    """The path of the program `name` (make, node, emcc), or skip or fail."""
    path = shutil.which(name)
    if path is None:
        missing(name, f"{name} not installed")
    return path


def find_c_compiler(environ) -> str | None:
    """$CC if set, else cc, gcc or clang from PATH."""
    if environ.get("CC"):
        return shutil.which(environ["CC"])
    return shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")


C_COMPILER = find_c_compiler(os.environ)


def require_cc() -> str:
    if C_COMPILER is None:
        missing("cc", "no C compiler ($CC, cc, gcc or clang) found")
    return C_COMPILER


# The random tests have fixed seeds and sizes, so every run checks the same
# cases. APIK_RANDOM_SCALE multiplies their sizes and APIK_RANDOM_SEED
# gives them other seeds: the weekly workflow sets both.
def random_settings() -> tuple[int, int | None]:
    """(scale, seed or None), from the environment."""
    values = {}
    for name, minimum in (("APIK_RANDOM_SCALE", 1), ("APIK_RANDOM_SEED", 0)):
        text = os.environ.get(name, "")
        if not text:
            continue
        if not text.isdigit() or int(text) < minimum:
            raise pytest.UsageError(f"{name} must be a whole number of at least {minimum}, not {text!r}")
        values[name] = int(text)
    return values.get("APIK_RANDOM_SCALE", 1), values.get("APIK_RANDOM_SEED")


def random_count(count: int) -> int:
    return count * random_settings()[0]


def random_seed(seed: int) -> int:
    """`seed`, or with APIK_RANDOM_SEED a seed made from both."""
    extra = random_settings()[1]
    return seed if extra is None else seed * 1_000_003 + extra + 1


def pytest_configure(config):
    required_tools()  # a misspelt APIK_REQUIRE stops the run at once
    random_settings()


def pytest_report_header(config):
    scale, seed = random_settings()
    if scale != 1 or seed is not None:
        return f"random tests: APIK_RANDOM_SCALE={scale} APIK_RANDOM_SEED={'' if seed is None else seed}"
    return None

STRICT_FLAGS = ["-std=c11", "-pedantic-errors", "-Wall", "-Wextra"]


def is_msvc(compiler: str | None) -> bool:
    """True for Microsoft's cl, which takes /flags instead of gcc's."""
    return compiler is not None and Path(compiler).stem.lower() == "cl"


# The same strictness for cl: C11, and its highest warning level that is
# not mostly about the system headers. Like -Wall, /W4 warns without failing.
MSVC_STRICT_FLAGS = ["/nologo", "/std:c11", "/W4"]


def werror_flags() -> list[str]:
    """The flag that turns warnings into errors, for this C compiler."""
    return ["/WX"] if is_msvc(C_COMPILER) else ["-Werror"]


def c_build_command(c_file: Path, exe: Path, flags=(), libraries=(), werror: bool = False) -> list[str]:
    """The command that builds `c_file` into `exe` with the strict flags,
    for gcc-style compilers or for cl. `werror` turns warnings into errors."""
    if is_msvc(C_COMPILER):
        # cl writes the object file to the current folder unless told where,
        # and its C library holds the maths functions (there is no -lm).
        return [C_COMPILER, *MSVC_STRICT_FLAGS, *(["/WX"] if werror else []), *flags,
                f"/Fe{exe}", f"/Fo{Path(exe).with_suffix('.obj')}", str(c_file)]
    return [C_COMPILER, *STRICT_FLAGS, *(["-Werror"] if werror else []), *flags, "-o", str(exe), str(c_file),
            *(f"-l{lib}" for lib in libraries)]
# Any undefined behaviour the generated C reaches stops the program with a
# sanitizer report (and a nonzero exit) instead of going unnoticed.
UBSAN_RUNTIME = ("-fsanitize=undefined", "-fno-sanitize-recover=all")
# Without UBSan's runtime library (MinGW-w64 gcc ships none, and some Linux
# gcc installs lack libubsan), a check that fires executes a trap instruction
# instead: the program still stops with a nonzero exit, but with no report.
UBSAN_TRAP = (*UBSAN_RUNTIME, "-fsanitize-trap=all")


def _links(flags: tuple[str, ...]) -> bool:
    """Whether the C compiler can build and link a program with `flags`."""
    with tempfile.TemporaryDirectory() as tmp:
        c_file = Path(tmp) / "probe.c"
        c_file.write_text("int main(void) { return 0; }\n", encoding="utf-8")
        exe = Path(tmp) / ("probe.exe" if os.name == "nt" else "probe")
        probe = subprocess.run([C_COMPILER, *flags, "-o", str(exe), str(c_file)], capture_output=True)
        return probe.returncode == 0


@functools.cache
def ubsan_flags() -> tuple[str, ...] | None:
    """The UBSan flags this C compiler can link: with the runtime if it can,
    else in trap mode, else None. Probed once, the first time a test builds
    with UBSan, so a run that builds nothing pays nothing."""
    if C_COMPILER is None or is_msvc(C_COMPILER):
        # cl has no UBSan, and only warns about the gcc flags it does not know.
        return None
    for flags in (UBSAN_RUNTIME, UBSAN_TRAP):
        if _links(flags):
            return flags
    return None


def require_ubsan() -> list[str]:
    """The UBSan flags, or skip the test when the compiler cannot build with
    UBSan at all."""
    require_cc()
    flags = ubsan_flags()
    if flags is None:
        missing("ubsan", "the C compiler cannot build with UBSan, not even in trap mode")
    return list(flags)


def extra_flags() -> list[str]:
    """APIK_SANITIZE=1 builds every end-to-end program with UBSan as well.
    Asking for it when UBSan cannot be built stops the run."""
    if os.environ.get("APIK_SANITIZE") != "1":
        return []
    flags = ubsan_flags()
    if flags is None:
        pytest.exit("APIK_SANITIZE=1, but the C compiler cannot build with UBSan", returncode=4)
    return list(flags)


def pytest_terminal_summary(terminalreporter):
    """Say so when the UBSan builds were not the full sanitizer."""
    if ubsan_flags.cache_info().currsize == 0:
        return  # nothing was built with UBSan
    flags = ubsan_flags()
    if flags is None:
        terminalreporter.write_line("UBSan: not available with this C compiler; the tests that need it were skipped")
    elif flags == UBSAN_TRAP:
        terminalreporter.write_line(
            "UBSan: trap mode (no runtime library): undefined behaviour still stops a program, but without a report"
        )


EXPECT = re.compile(r"# expect: (?P<code>[EW]\d{4}) at (?P<line>\d+):(?P<column>\d+)$")


def expected_diagnostics(source: str) -> list[tuple[str, int, int]]:
    """The `# expect: <code> at <line>:<column>` lines of a program that must
    be rejected, as (code, line, column), in order."""
    found = []
    for line in source.splitlines():
        if line.startswith("# expect:"):
            match = EXPECT.match(line)
            assert match, f"malformed expectation: {line!r}"
            found.append((match["code"], int(match["line"]), int(match["column"])))
    return found


@pytest.fixture(scope="session")
def compiler() -> Compiler:
    return Compiler()


@pytest.fixture
def build_apik(compiler, tmp_path):
    """Compile APIK26 source to a native binary; returns a function that runs it.

    The generated C is built with strict flags so that non-conforming output
    (for example a label at the end of a block) fails the test. Skipped when
    no C compiler is installed.
    """
    require_cc()

    def build(source: str, flags: list[str]):
        result = compiler.compile(source, filename="t.apik")
        assert result.ok, result.render()
        c_file = tmp_path / "prog.c"
        c_file.write_text(result.c_source, encoding="utf-8")
        exe = tmp_path / ("prog.exe" if os.name == "nt" else "prog")
        build = subprocess.run(
            c_build_command(c_file, exe, flags, result.link_libraries),
            capture_output=True, text=True,
        )
        # cl reports errors on stdout.
        assert build.returncode == 0, f"{build.stderr}{build.stdout}\n--- generated C ---\n{result.c_source}"

        def run(stdin: str):
            # The program writes UTF-8; the locale encoding (cp1252 on
            # Windows) would misread non-ASCII text.
            return subprocess.run([str(exe)], input=stdin, capture_output=True, text=True,
                                  encoding="utf-8", timeout=10)

        return run

    return build


@pytest.fixture
def run_apik(build_apik):
    """Build and run APIK26 source; returns its stdout. It must exit with 0."""

    def run(source: str, stdin: str = "") -> str:
        proc = build_apik(source, extra_flags())(stdin)
        assert proc.returncode == 0, proc.stderr
        return proc.stdout

    return run


@pytest.fixture
def run_trapping(build_apik):
    """Build APIK26 source with UBSan and run it, expecting a runtime error.

    Returns its stderr. An APIK26 runtime check must stop the program *before*
    any undefined behaviour: if a check is missing, UBSan reports first and
    the stderr no longer matches.
    """

    def run(source: str, stdin: str = "") -> str:
        proc = build_apik(source, require_ubsan())(stdin)
        assert proc.returncode != 0, proc.stdout
        return proc.stderr

    return run


@pytest.fixture
def run_trapping_or_output(build_apik):
    """Build with UBSan and run; returns (exit status, stdout). For checking
    that a program finishes without reaching a runtime error it guards."""

    def run(source: str, stdin: str = "") -> tuple[int, str]:
        proc = build_apik(source, require_ubsan())(stdin)
        return proc.returncode, proc.stdout

    return run
