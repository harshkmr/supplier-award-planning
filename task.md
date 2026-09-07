# Tasks — Harden Python Supplier Award Planning with Valgrind

## Ticket 01: Project Scaffold & Build System ✅
- [x] `pyproject.toml`
- [x] `supplier_award/__init__.py`
- [x] `supplier_award/exceptions.py`
- [x] `CODING_STANDARDS.md`
- [x] `pip install -e .` succeeds and `import supplier_award` works

## Ticket 02: C Extension for Container Utilization Scoring ✅
- [x] `src/_container_util.c`
- [x] `tests/test_container_util.py`
- [x] Compiles cleanly on MSVC (/W4), all 14 tests pass

## Ticket 03: Safe YAML Configuration Loader ✅
- [x] `supplier_award/config.py`
- [x] `data/sample_config.yaml`
- [x] `data/bad_configs/*.yaml` (3 files)
- [x] `tests/test_config.py`
- [x] All 16 tests pass (including AST-based yaml.load source scan)

## Ticket 04: FX Rate Fetcher with Caching & Staleness ✅
- [x] `supplier_award/fx.py`
- [x] `tests/test_fx.py`
- [x] All 8 tests pass

## Ticket 05: Award Planner Engine ✅
- [x] `supplier_award/planner.py`
- [x] `tests/test_planner.py`
- [x] All 11 tests pass

## Ticket 06: Golden File Verification ✅
- [x] `supplier_award/golden.py`
- [x] `data/golden/expected_award_plan.json`
- [x] `tests/test_golden.py`
- [x] All 7 tests pass

## Ticket 07: CLI Entry Point & End-to-End Tests ✅
- [x] `supplier_award/cli.py`
- [x] `supplier_award/__main__.py`
- [x] End-to-end tests in test_planner.py (determinism, golden comparison)

## Ticket 08: Valgrind Verification Scripts ✅
- [x] `tests/valgrind_runner.py` — exercises all code paths, 1000-call stress test
- [x] `tests/valgrind_check.sh` — Valgrind wrapper with CPython suppressions

## Ticket 09: README & Final Documentation ✅
- [x] `README.md` — installation, usage, architecture, Valgrind, algorithm
- [x] Module docstrings finalized
- [x] Full test suite passes: 56/56
