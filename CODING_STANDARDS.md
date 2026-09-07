# Coding Standards

## Python

- **Python 3.10+** — use modern typing (`X | None`, not `Optional[X]`).
- **`yaml.safe_load()` only** — never use `yaml.load()` without a safe Loader. This is a security-critical rule.
- **Explicit validation** — every public function that accepts external data must validate it and raise a typed exception from `supplier_award.exceptions`. Never silently accept bad input.
- **Deterministic output** — JSON serialisation must use `sort_keys=True` and consistent float formatting so golden-file comparisons are stable.
- **Docstrings** — every public module, class, and function gets a docstring (Google style).
- **No bare `except`** — always catch a specific exception type.

## C Extension (`_container_util`)

- **Compile flags** — always build with `-Wall -Wextra`. CI will use `-Werror`.
- **Reference counting** — every `PyObject*` must be `Py_DECREF`'d on every code path, including error paths. Use `goto error;` pattern for cleanup.
- **Input validation** — use `PyArg_ParseTuple` and validate numeric ranges before any arithmetic.
- **Error signalling** — set a Python exception (`PyErr_SetString`) and return `NULL` on every error path. Never return a value after setting an exception.
- **Valgrind-clean** — the extension must produce zero errors, zero leaks, and zero warnings under `valgrind --leak-check=full`.

## Testing

- **Test at public seams** — test `load_config()`, `fetch_rates()`, `score_utilization()`, and `plan()`. Don't test private helpers directly.
- **No tautological assertions** — expected values come from worked examples or the spec, never recomputed by the same formula under test.
- **Mock the network** — FX tests use `unittest.mock.patch` on `requests.get`. Never hit a live API in CI.
- **Golden files** — end-to-end tests compare planner output against checked-in JSON files with pinned FX rates.
