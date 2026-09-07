#!/usr/bin/env bash
# valgrind_check.sh — Run Valgrind memcheck on the C extension.
#
# REQUIREMENTS:
#   - Linux (Valgrind does not support Windows or macOS natively)
#   - valgrind installed (apt install valgrind / dnf install valgrind)
#   - CPython built with debug symbols (recommended for accurate traces)
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

# CPython has some known false-positive leaks.  Use the suppression
# file shipped with CPython if available.
PYTHON_DIR="$(python3 -c 'import sys; print(sys.prefix)')"
SUPPRESSIONS=""
if [ -f "$PYTHON_DIR/Misc/valgrind-python.supp" ]; then
    SUPPRESSIONS="--suppressions=$PYTHON_DIR/Misc/valgrind-python.supp"
fi

echo "=== Valgrind memcheck for _container_util ==="
echo "Project:      $PROJECT_DIR"
echo "Runner:       $RUNNER"
echo "Suppressions: ${SUPPRESSIONS:-none}"
echo ""

valgrind \
    --leak-check=full \
    --show-leak-kinds=all \
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
