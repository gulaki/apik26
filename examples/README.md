# APIK26 examples

| Folder | What it holds | Status |
|---|---|---|
| `*.apik` (this folder) | Programs for the language as it exists today. Each has a recorded run in `tests/test_end_to_end.py`. | works |
| `errors/` | Programs the compiler rejects today. The header lists every error the file must produce, one `# expect: <code> at <line>:<column>` line each (`# expect: E0201 at 3:11`). | works |
| `future/` | **Proposed** syntax for later versions: more scalar types, functions (`global`, `mut`), runtime errors and tracebacks, overloading, unions, arrays, classes, iterators. | rejected today |
| `future/errors/` | Programs the *future* compiler must reject, with the diagnostic we want. | rejected today |

Try them:

```sh
mkdir -p build
apik26 examples/primes.apik -o build/primes.c
cc -std=c11 -o build/primes build/primes.c && echo 30 | build/primes
```

Or in a browser, with Emscripten installed (see the main README):
`apik26 examples/primes.apik --target wasm --build make`, then
`make -C examples/primes` and `python -m http.server` in `examples/primes/`.
Those folders are ignored by git.

Every feature these programs use is explained in the
[language reference](../docs/language.md).

Highlights: `types.apik` (declarations, casts, chained and multiple
assignment), `booleans.apik` (truth tests, short-circuit `and`/`or`,
comparison chains), `fibonacci.apik` (`a, b = b, a + b`), `gcd.apik` (`%`),
`primes.apik` (nested loops, `continue` of a named outer loop), `loop_break.apik` (`break`), `f2c.apik` (types inferred through an expression) and `newton_sqrt.apik` (float math, early exit,
block-scoped temporaries).

`tests/test_example_folders.py` checks that every `errors/` file reports exactly
the errors its header lists (nothing missing, nothing extra), that every error
code has at least one `errors/` example, and that every `future/` file is still
rejected. Run one to see the output: `apik26 examples/errors/many_syntax_errors.apik`. When a
feature ships, move its example up a level and record its run.
The `future/` syntax is a design sketch, not a commitment; the reasoning is in
[`docs/whitepaper.md`](../docs/whitepaper.md).
