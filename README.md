# Supplier Award Planning

**Harden supplier award planning with ISO container limits, live FX rates, and a Valgrind-clean C extension.**

A Python library that ranks purchase-order awards across EUR, GBP, and USD suppliers by combining quoted unit costs, ISO shipping container weight limits, and historical FX rates fetched live from the [Frankfurter.app](https://api.frankfurter.dev) public API. A CPython C extension handles container utilization scoring and is designed to run cleanly under Valgrind.

## Features

- **Safe YAML configuration** — uses `yaml.safe_load()` exclusively; rejects insecure YAML, missing fields, and overweight allocations at load time
- **Live FX rates** — fetches from Frankfurter.app v2 API with local caching, staleness detection, and offline fallback
- **ISO container limits** — enforces 20ft TEU (30,480 kg max gross) and 40ft FEU (34,000 kg) per ISO 668/1496-1
- **C extension** — `_container_util.score_utilization()` for fast container utilization scoring, designed Valgrind-clean
- **Golden file verification** — deterministic JSON output compared against checked-in golden files
- **Comprehensive test suite** — 56 tests covering config validation, FX mocking, C extension edge cases, and end-to-end planning

## Installation

```bash
# Clone and install in development mode
git clone <your-repo-url>
cd supplier-award-planning
pip install -e ".[dev]"
```

Requires:
- Python 3.10+
- A C compiler (MSVC on Windows, GCC/Clang on Linux/macOS)
- `pyyaml`, `requests` (installed automatically)

## Quick Start

```bash
# Generate an award plan from the sample configuration
python -m supplier_award plan data/sample_config.yaml
```

Output (JSON):
```json
{
  "awards": [
    {
      "rank": 1,
      "supplier": "Acme GmbH",
      "currency": "EUR",
      "unit_cost": 12.5,
      "normalized_cost": 12.5,
      "effective_cost": 12.5007,
      "utilization": 0.9999
    }
  ],
  "metadata": {
    "base_currency": "EUR",
    "container_type": "20ft",
    "fx_rates": {"GBP": 0.856, "USD": 1.085}
  }
}
```

### Compare Against Golden File

```bash
python -m supplier_award plan data/sample_config.yaml --golden data/golden/expected_award_plan.json
```

## Configuration

Create a YAML file (see [`data/sample_config.yaml`](data/sample_config.yaml)):

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
```

### Validation Rules

| Field | Rule |
|-------|------|
| `base_currency` | Must be `EUR`, `GBP`, or `USD` |
| `container_type` | Must be `20ft` or `40ft` |
| `staleness_hours` | Positive number (default: 24) |
| `unit_cost` | Must be > 0 |
| `weight_per_unit_kg` | Must be > 0; a single unit must fit in the container |
| `currency` | Must be `EUR`, `GBP`, or `USD` |

## Architecture

```
supplier_award/
├── __init__.py          # Package init, public API exports
├── __main__.py          # python -m supplier_award entry point
├── cli.py               # CLI with argparse (plan subcommand)
├── config.py            # Safe YAML loader with validation
├── exceptions.py        # Typed exceptions hierarchy
├── fx.py                # Frankfurter.app v2 FX client with caching
├── golden.py            # Deterministic JSON serialization & comparison
└── planner.py           # Core ranking engine

src/
└── _container_util.c    # CPython C extension (Valgrind-clean)

tests/
├── conftest.py          # Shared fixtures
├── test_config.py       # Config loading & validation (16 tests)
├── test_container_util.py  # C extension correctness (14 tests)
├── test_fx.py           # FX fetching with mocks (8 tests)
├── test_golden.py       # Golden file comparison (7 tests)
├── test_planner.py      # End-to-end planning (11 tests)
├── valgrind_runner.py   # Exercises all C paths for Valgrind
└── valgrind_check.sh    # Valgrind wrapper script (Linux)
```

## Testing

```bash
# Run the full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=supplier_award --cov-report=term-missing
```

## Valgrind Verification

> **Note:** Valgrind runs on Linux only.

```bash
# Quick check
valgrind --leak-check=full --error-exitcode=1 \
  python -c "from supplier_award._container_util import score_utilization; score_utilization(25000, 2200, 30480)"

# Full verification (all code paths)
bash tests/valgrind_check.sh
```

The C extension is designed to be Valgrind-clean:
- Proper `Py_INCREF`/`Py_DECREF` reference counting
- No memory allocations beyond Python object creation
- `NULL` return with exception set on every error path
- `PyFloat_FromDouble` returns a new reference (no leak)

## Award Ranking Algorithm

1. Fetch live FX rates (or use cache/pinned rates)
2. For each supplier: normalize `unit_cost` to base currency
3. Compute `max_units_per_container = ⌊max_payload / weight_per_unit⌋`
4. Compute `utilization = (max_units × weight_per_unit) / payload_capacity` via C extension
5. Compute `effective_cost = normalized_cost / utilization`
6. Rank suppliers by `effective_cost` ascending (lower = better)

## License

MIT
