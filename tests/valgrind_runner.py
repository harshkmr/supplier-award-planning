"""Valgrind runner — exercises all C extension code paths.

Run under Valgrind to verify zero memory errors and zero leaks:

    valgrind --leak-check=full --show-leak-kinds=all \\
             --error-exitcode=1 \\
             python tests/valgrind_runner.py

This script is designed for Linux only. On Windows, use the
pytest test suite for correctness (but not memory safety) verification.
"""

import sys


def main():
    """Exercise every code path in _container_util.score_utilization."""
    from supplier_award._container_util import score_utilization

    errors = 0

    # --- Normal cases ---
    print("Testing normal cases...")

    # Full utilization (20ft TEU)
    result = score_utilization(28280.0, 2200.0, 30480.0)
    assert abs(result - 1.0) < 1e-9, f"Expected 1.0, got {result}"

    # Half utilization
    result = score_utilization(14140.0, 2200.0, 30480.0)
    assert abs(result - 0.5) < 1e-9, f"Expected 0.5, got {result}"

    # Zero cargo
    result = score_utilization(0.0, 2200.0, 30480.0)
    assert abs(result) < 1e-9, f"Expected 0.0, got {result}"

    # Small cargo
    result = score_utilization(1.0, 2200.0, 30480.0)
    expected = 1.0 / 28280.0
    assert abs(result - expected) < 1e-12, f"Expected {expected}, got {result}"

    # 40ft container
    result = score_utilization(25000.0, 3800.0, 34000.0)
    expected = 25000.0 / 30200.0
    assert abs(result - expected) < 1e-9, f"Expected {expected}, got {result}"

    print("  Normal cases: PASS")

    # --- Error cases (must not leak on error paths) ---
    print("Testing error paths...")

    # Negative cargo
    try:
        score_utilization(-1.0, 2200.0, 30480.0)
        print("  ERROR: should have raised ValueError for negative cargo")
        errors += 1
    except ValueError:
        pass

    # Negative tare
    try:
        score_utilization(1000.0, -1.0, 30480.0)
        print("  ERROR: should have raised ValueError for negative tare")
        errors += 1
    except ValueError:
        pass

    # Negative max_gross
    try:
        score_utilization(1000.0, 2200.0, -1.0)
        print("  ERROR: should have raised ValueError for negative max_gross")
        errors += 1
    except ValueError:
        pass

    # max_gross == tare
    try:
        score_utilization(1000.0, 5000.0, 5000.0)
        print("  ERROR: should have raised ValueError for zero payload")
        errors += 1
    except ValueError:
        pass

    # max_gross < tare
    try:
        score_utilization(1000.0, 5000.0, 3000.0)
        print("  ERROR: should have raised ValueError for negative payload")
        errors += 1
    except ValueError:
        pass

    # Overweight
    try:
        score_utilization(30000.0, 2200.0, 30480.0)
        print("  ERROR: should have raised OverflowError for overweight")
        errors += 1
    except OverflowError:
        pass

    # Wrong argument count
    try:
        score_utilization(1000.0, 2200.0)
        print("  ERROR: should have raised TypeError for missing arg")
        errors += 1
    except TypeError:
        pass

    # Wrong argument type
    try:
        score_utilization("abc", 2200.0, 30480.0)
        print("  ERROR: should have raised TypeError for string arg")
        errors += 1
    except TypeError:
        pass

    print("  Error paths: PASS")

    # --- Stress test (exercise allocator) ---
    print("Testing allocator stress (1000 calls)...")
    for i in range(1000):
        cargo = float(i) * 28.28
        if cargo > 28280.0:
            try:
                score_utilization(cargo, 2200.0, 30480.0)
            except OverflowError:
                pass
        else:
            score_utilization(cargo, 2200.0, 30480.0)
    print("  Stress test: PASS")

    if errors > 0:
        print(f"\nFAILED: {errors} error(s)")
        return 1

    print("\nAll Valgrind runner checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
