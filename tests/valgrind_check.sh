#!/usr/bin/env bash
# valgrind_check.sh — Run Valgrind memcheck on the C extension.
#
# REQUIREMENTS:
#   - Linux (Valgrind does not support Windows or macOS natively)
#   - valgrind installed (apt install valgrind / dnf install valgrind)
#
# USAGE:
#   bash tests/valgrind_check.sh
#
# EXIT CODE:
#   0 if Valgrind reports zero errors and zero leaks
#   1 otherwise

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RUNNER="$SCRIPT_DIR/valgrind_runner.py"

# Disable Python's pymalloc allocator so Valgrind uses system malloc/free
export PYTHONMALLOC=malloc

# Use suppression file for known CPython runtime false positives
SUPPRESSIONS="--suppressions=$SCRIPT_DIR/valgrind-python.supp"

echo "=== Valgrind memcheck for _container_util ==="
echo "Project:      $PROJECT_DIR"
echo "Runner:       $RUNNER"
echo "Suppressions: $SUPPRESSIONS"
echo "PYTHONMALLOC: $PYTHONMALLOC"
echo ""

# We check for definite memory leaks in the C extension.
# CPython runtime caches are suppressed via valgrind-python.supp.
valgrind \
    --tool=memcheck \
    --leak-check=full \
    --show-leak-kinds=definite \
    --errors-for-leak-kinds=definite \
    --track-origins=yes \
    --error-exitcode=1 \
    $SUPPRESSIONS \
    python3 "$RUNNER"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ Valgrind: CLEAN — zero errors, zero leaks."
else
    echo ""
    echo "✗ Valgrind: FAILED — see above for details."
fi

exit $EXIT_CODE
