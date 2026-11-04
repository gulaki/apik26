# Contributing

Scribe has no license yet, so it is not open to outside contributions. This
guide is how changes are made here, by the maintainer and by AI assistants
working with them.

## The rule

Scribe compiles to strictly conforming ISO C, and a program that compiles
must never reach undefined behaviour. Every change keeps that true, and
keeps what already works working: [CI](.github/workflows/ci.yml) runs
the whole test suite on Linux, macOS, Windows and WebAssembly before
anything is merged.

## How a change is made

1. **One numbered task per pull request**, small enough to review in one
   sitting. Larger features are split into steps first, as in
   [`docs/design/functions.md`](docs/design/functions.md#10-roadmap).
2. **Failing tests first.** The first commit adds tests that show the bug
   or the missing feature, and they fail. The fix follows in later commits.
3. **Small commits**, each with one purpose, titled with a prefix:
   `test:`, `feat:`, `fix:`, `docs:`, `build:` or `ci:`, then a capitalised
   summary, for example `feat: Allow // and % on floats`.
4. **Docs in the same pull request.** The language reference
   ([`docs/language.md`](docs/language.md)), the design notes and the error
   catalogue ([`docs/errors.md`](docs/errors.md)) describe the language as
   it is. `tests/test_docs.py` compiles and runs every example in them.
5. **A changelog entry.** A pull request that changes `scribe_lang/` adds
   an entry under "Unreleased" in [`CHANGELOG.md`](CHANGELOG.md), and the
   [Changelog check](.github/workflows/changelog.yml) fails without one. A
   change with nothing to tell users (a refactor, a test) takes the
   `no-changelog` label instead.
6. **Releases.** After the merge, a small release pull request moves the
   "Unreleased" entries under a new version heading and writes the same
   version in `VERSION.txt` (the rules are at the top of the changelog). When
   it is merged, the [Release workflow](.github/workflows/release.yml) tags
   `vX.Y.Z` and publishes a GitHub Release with that section as its notes.

## Running the tests

```sh
pip install -e ".[test]"
python -m pytest                     # everything
SCRIBE_SANITIZE=1 python -m pytest   # also build every program with UBSan
python -m pytest --cov               # with coverage of scribe_lang/
```

Coverage must not drop below `fail_under` in `pyproject.toml`; CI checks
it. When a change raises it, raise `fail_under` too.

A test that needs a missing tool (a C compiler, UBSan, make, node, emcc)
skips itself locally. CI names the tools each job must have in
`SCRIBE_REQUIRE`, and there a missing tool fails the test instead.

## Error codes

Codes are never renumbered or reused. See
[Adding an error](docs/errors.md#adding-an-error) and, for codes no longer
reported, [Retired codes](docs/errors.md#retired-codes).

## Not in the repository

Build outputs and binaries: generated C, executables, the folders that
`--target wasm` writes next to the examples.
