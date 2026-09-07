# Harden Python Supplier Award Planning with Valgrind

A Python + C project: a supplier award planning library that ranks purchase-order awards across EUR, GBP, and USD suppliers by combining quoted unit costs, ISO shipping container limits, and live FX rates from Frankfurter.app. Includes a CPython C extension for container utilization scoring that must run cleanly under Valgrind.

## Problem Statement

Procurement teams need to rank and allocate purchase-order awards across international suppliers denominated in EUR, GBP, and USD. Today's partially implemented planner has several critical defects:

1. **Insecure YAML defaults** — the config loader uses `yaml.load()` (unsafe) instead of `yaml.safe_load()`, and the default configuration silently approves allocations that exceed ISO container gross weight limits (30,480 kg for 20ft TEU, 34,000 kg for 40ft).
2. **Buggy C extension** — the CPython C helper for container utilization scoring has memory leaks, potential buffer overflows, and reference-counting errors that Valgrind would catch.
3. **No FX verification** — currency conversions are hardcoded rather than fetched from a live source, allowing stale rates to silently distort award rankings.
4. **No golden-file verification** — there is no mechanism to verify that award plans match expected golden JSON output.

## Solution

Build the complete supplier award planning package from scratch with security and correctness as first-class concerns:

- **Safe YAML configuration** with strict validation — reject any allocation that would exceed ISO container limits.
- **Live FX rate fetching** from the [Frankfurter.app v2 API](https://api.frankfurter.dev/v2/rates) with fallback and staleness checks.
- **A correct CPython C extension** (`_container_util`) for container utilization scoring that passes Valgrind's memcheck with zero errors/leaks.
- **Golden JSON verification** — deterministic award plan output compared against checked-in golden files.

## User Stories

1. As a procurement engineer, I want to load supplier configurations from a YAML file using safe parsing, so that arbitrary code execution via YAML is impossible.
2. As a procurement engineer, I want the system to reject any allocation where the total cargo weight exceeds the ISO container maximum gross weight (30,480 kg for 20ft, 34,000 kg for 40ft), so that overweight containers are never silently approved.
3. As a procurement engineer, I want supplier quotes in EUR, GBP, and USD to be normalized to a single base currency using live FX rates from Frankfurter.app, so that award rankings reflect current market conditions.
4. As a procurement engineer, I want the system to raise an error if FX rates are older than a configurable staleness threshold (default 24 hours), so that stale rates cannot silently distort rankings.
5. As a procurement engineer, I want the system to provide a fallback FX mechanism (cached rates file) when the network is unavailable, so that planning can proceed offline with explicit warnings.
6. As a procurement engineer, I want container utilization scores to be computed by a C extension for performance, so that large procurement datasets are scored efficiently.
7. As a security engineer, I want the C extension to run under Valgrind memcheck with zero errors, zero leaks, and zero warnings, so that memory safety is proven.
8. As a procurement engineer, I want the award planner to produce deterministic JSON output, so that regression testing can compare against golden files.
9. As a procurement engineer, I want the planner to rank suppliers by effective cost per unit (FX-normalized quote ÷ container utilization score), so that I can select the most cost-effective allocation.
10. As a procurement engineer, I want the system to flag any supplier whose quoted weight per unit is missing or zero, so that unverified freight data cannot enter the ranking.
11. As a QA engineer, I want a test suite that covers config validation, FX fetching, container scoring, and end-to-end award planning against golden files, so that regressions are caught automatically.
12. As a developer, I want the C extension to be buildable with a standard `setup.py` / `pyproject.toml`, so that `pip install -e .` works out of the box.

## Implementation Decisions

### Architecture

The package is structured as `supplier_award/` with these modules:

- **`config.py`** — YAML configuration loader using `yaml.safe_load()`. Validates container type, weight limits, supplier fields. Rejects overweight allocations at load time.
- **`fx.py`** — FX rate fetcher hitting `https://api.frankfurter.dev/v2/rates?base=EUR&quotes=GBP,USD`. Supports caching, staleness checks, and offline fallback from a JSON cache file.
- **`planner.py`** — The core award planning engine. Normalizes quotes to base currency, calls the C extension for utilization scoring, ranks suppliers, produces the award plan as a Python dict.
- **`_container_util.c`** — CPython C extension module. Exports `score_utilization(cargo_weight_kg, tare_weight_kg, max_gross_kg)` → float in [0.0, 1.0]. Validates inputs, handles edge cases (zero max_gross, negative weights). Must be Valgrind-clean.
- **`golden.py`** — Golden file comparison utility. Serializes award plans to deterministic JSON (sorted keys, consistent float formatting) and compares against checked-in `.json` files.
- **`cli.py`** — Simple CLI entry point: `python -m supplier_award plan config.yaml`.

### Container Types & Weight Limits (ISO 668 / ISO 1496-1)

| Container | Tare (kg) | Max Gross (kg) | Max Payload (kg) |
|-----------|-----------|----------------|-------------------|
| 20ft TEU  | 2,200     | 30,480         | 28,280            |
| 40ft FEU  | 3,800     | 34,000         | 30,200            |

### C Extension Design

```c
// _container_util.c
// score_utilization(cargo_weight_kg, tare_weight_kg, max_gross_kg) -> float
// Returns cargo_weight_kg / (max_gross_kg - tare_weight_kg)
// Raises ValueError for invalid inputs (negative weights, max_gross <= tare)
// Raises OverflowError if utilization > 1.0 (overweight)
```

The C extension must:
- Use proper `Py_INCREF`/`Py_DECREF` reference counting
- Not leak memory on any error path
- Use `PyArg_ParseTuple` safely
- Return Python float objects correctly
- Compile cleanly with `-Wall -Wextra -Werror`

### YAML Configuration Schema

```yaml
base_currency: EUR
staleness_hours: 24
container_type: 20ft  # or 40ft
suppliers:
  - name: "Acme GmbH"
    currency: EUR
    unit_cost: 12.50
    weight_per_unit_kg: 2.3
    units_offered: 5000
  - name: "BritParts Ltd"
    currency: GBP
    unit_cost: 11.00
    weight_per_unit_kg: 2.1
    units_offered: 3000
  - name: "USSupply Inc"
    currency: USD
    unit_cost: 14.00
    weight_per_unit_kg: 2.5
    units_offered: 8000
```

Validation rules:
- `yaml.safe_load()` only — never `yaml.load()`
- All `weight_per_unit_kg` must be > 0
- All `unit_cost` must be > 0
- `container_type` must be `20ft` or `40ft`
- `currency` must be one of `EUR`, `GBP`, `USD`
- `staleness_hours` must be > 0, default 24

### FX Rate Fetching

- Primary: `GET https://api.frankfurter.dev/v2/rates?base={base_currency}&quotes=GBP,USD`
- Cache results to `~/.supplier_award/fx_cache.json` with timestamp
- On network failure, fall back to cache with a logged warning
- Raise `StaleRatesError` if cached rates are older than `staleness_hours`

### Award Ranking Algorithm

1. Fetch/load FX rates
2. For each supplier: normalize `unit_cost` to base currency using FX rate
3. For each supplier: compute `max_units_per_container = floor(max_payload_kg / weight_per_unit_kg)`
4. For each supplier: compute `utilization = (max_units_per_container * weight_per_unit_kg) / max_payload_kg` via C extension
5. For each supplier: `effective_cost = normalized_unit_cost / utilization`
6. Rank by `effective_cost` ascending (lower is better)
7. Reject any supplier where `max_units_per_container * weight_per_unit_kg > max_payload_kg`

### Golden File Format

```json
{
  "metadata": {
    "base_currency": "EUR",
    "container_type": "20ft",
    "fx_rates": {"GBP": 0.856, "USD": 1.085},
    "generated_at": "2025-01-15T10:00:00Z"
  },
  "awards": [
    {
      "rank": 1,
      "supplier": "Acme GmbH",
      "currency": "EUR",
      "unit_cost": 12.50,
      "normalized_cost_eur": 12.50,
      "weight_per_unit_kg": 2.3,
      "max_units_per_container": 12295,
      "utilization": 0.9999,
      "effective_cost": 12.5012
    }
  ]
}
```

## Testing Decisions

### Test Seams

The primary seam is the **`planner.plan(config_path)` function** — the public interface that accepts a YAML config path and returns an award plan dict. All end-to-end tests operate at this seam.

Secondary seams for unit testing:
- `config.load_config(path)` — config loading and validation
- `fx.fetch_rates(base, quotes)` — FX rate fetching (mocked network in tests)
- `_container_util.score_utilization(cargo, tare, max_gross)` — C extension correctness

### Test Strategy

1. **Config validation tests** — ensure bad YAML is rejected (unsafe load, missing fields, zero/negative weights, invalid container types)
2. **FX tests** — mock HTTP responses, test staleness detection, test fallback behavior
3. **C extension tests** — test normal cases, edge cases (zero, negative, overweight), verify error types
4. **Integration tests** — run the full planner with sample data and compare against golden JSON
5. **Valgrind tests** — run a Python script that exercises the C extension under Valgrind, assert zero errors

### Test Commands

```bash
# Unit and integration tests
pytest tests/ -v

# Valgrind check (Linux only — the Valgrind verification)
valgrind --leak-check=full --error-exitcode=1 python -c "from supplier_award._container_util import score_utilization; score_utilization(25000, 2200, 30480)"

# Full Valgrind test script
valgrind --leak-check=full --show-leak-kinds=all --error-exitcode=1 python tests/valgrind_runner.py
```

## Proposed Changes

### Core Package — `supplier_award/`

#### [NEW] `pyproject.toml`
Build configuration with setuptools, C extension compilation flags (`-Wall -Wextra -Werror`), and project metadata. Dependencies: `pyyaml`, `requests`.

#### [NEW] `supplier_award/__init__.py`
Package init, exports `plan`, `load_config`, `fetch_rates`.

#### [NEW] `supplier_award/config.py`
Safe YAML loader with schema validation. Rejects insecure defaults, overweight allocations, missing/zero weights.

#### [NEW] `supplier_award/fx.py`
Frankfurter.app v2 API client with caching and staleness detection. Raises `StaleRatesError`, `FXFetchError`.

#### [NEW] `supplier_award/planner.py`
Core ranking engine. Normalizes costs via FX, calls C extension for utilization, produces deterministic award plans.

#### [NEW] `supplier_award/golden.py`
Golden file comparison. Deterministic JSON serialization, diff reporting.

#### [NEW] `supplier_award/cli.py`
`python -m supplier_award plan config.yaml` entry point.

#### [NEW] `supplier_award/exceptions.py`
Custom exceptions: `ConfigValidationError`, `StaleRatesError`, `FXFetchError`, `OverweightError`, `InvalidSupplierError`.

---

### C Extension — `src/`

#### [NEW] `src/_container_util.c`
CPython C extension. Exports `score_utilization()`. Strict input validation, proper refcounting, Valgrind-clean.

---

### Sample Data — `data/`

#### [NEW] `data/sample_config.yaml`
Example procurement config with 3 suppliers (EUR, GBP, USD).

#### [NEW] `data/golden/expected_award_plan.json`
Golden JSON output for the sample config with pinned FX rates.

#### [NEW] `data/bad_configs/overweight.yaml`
Config where a supplier's allocation exceeds container limits — must be rejected.

#### [NEW] `data/bad_configs/unsafe_yaml.yaml`
Config that would exploit `yaml.load()` — must be rejected by safe loader.

#### [NEW] `data/bad_configs/missing_weight.yaml`
Config with missing `weight_per_unit_kg` — must be rejected.

---

### Tests — `tests/`

#### [NEW] `tests/conftest.py`
Shared fixtures: sample configs, mocked FX responses, temp directories.

#### [NEW] `tests/test_config.py`
Config loading and validation tests.

#### [NEW] `tests/test_fx.py`
FX fetching tests with mocked HTTP, staleness, fallback.

#### [NEW] `tests/test_container_util.py`
C extension unit tests — normal, edge, error cases.

#### [NEW] `tests/test_planner.py`
End-to-end planner tests against golden files.

#### [NEW] `tests/test_golden.py`
Golden file comparison utility tests.

#### [NEW] `tests/valgrind_runner.py`
Script that exercises all C extension code paths for Valgrind analysis.

#### [NEW] `tests/valgrind_check.sh`
Shell script to run Valgrind with proper suppressions and exit code checking.

---

### Documentation

#### [NEW] `README.md`
Project overview, installation, usage, Valgrind verification instructions.

#### [NEW] `CODING_STANDARDS.md`
Coding standards for the project — Python style, C extension rules, testing conventions.

## Verification Plan

### Automated Tests

```bash
# Build the C extension
pip install -e .

# Run the full test suite
pytest tests/ -v --tb=short

# Run Valgrind check (on Linux)
bash tests/valgrind_check.sh
```

### Manual Verification

1. Run `python -m supplier_award plan data/sample_config.yaml` and confirm output matches golden file
2. Try loading `data/bad_configs/overweight.yaml` — confirm it raises `OverweightError`
3. Try loading `data/bad_configs/unsafe_yaml.yaml` — confirm it's rejected safely
4. Disconnect network and verify FX fallback works with cached rates
5. Run Valgrind on a Linux system and confirm zero errors/leaks

> [!IMPORTANT]
> **Valgrind limitation**: Valgrind only runs on Linux. The Valgrind verification scripts are designed for Linux environments. On Windows, the C extension tests provide correctness coverage but not memory safety verification. A CI pipeline on Linux would be needed for automated Valgrind checks.

## Open Questions

> [!IMPORTANT]
> 1. **Issue tracker**: There is no issue tracker configured for this workspace. Tickets will be written as local files under `.scratch/tickets/`. Is that acceptable, or do you have a GitHub repo to publish to?

> [!NOTE]
> 2. **FX rate pinning for golden tests**: The golden file tests need deterministic FX rates. The plan is to mock the FX response in tests and pin rates in the golden file metadata. This means golden tests don't hit the network.

> [!NOTE]
> 3. **Python version target**: Planning for Python 3.10+ (for `match` statements and modern typing). Let me know if you need older compatibility.
