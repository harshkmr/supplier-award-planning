"""Golden file comparison for deterministic award plan verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def serialize(plan: dict[str, Any]) -> str:
    """Serialize an award plan to deterministic JSON.

    Uses sorted keys, 2-space indentation, and a trailing newline
    so that golden file diffs are minimal and readable.

    Args:
        plan: Award plan dictionary from ``planner.plan()``.

    Returns:
        Deterministic JSON string.
    """
    return json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compare(
    plan: dict[str, Any],
    golden_path: str | Path,
) -> tuple[bool, str]:
    """Compare an award plan against a golden JSON file.

    Args:
        plan: Award plan dictionary from ``planner.plan()``.
        golden_path: Path to the golden JSON file.

    Returns:
        A tuple of ``(match, detail)``.  *match* is True if the plan
        matches the golden file.  *detail* is empty on match, or a
        human-readable description of the first difference.

    Raises:
        FileNotFoundError: If *golden_path* does not exist.
    """
    golden_path = Path(golden_path)
    if not golden_path.is_file():
        raise FileNotFoundError(f"Golden file not found: {golden_path}")

    with open(golden_path, "r", encoding="utf-8") as fh:
        golden = json.load(fh)

    # Strip metadata.generated_at from both sides — timestamps are non-deterministic
    plan_cmp = _strip_volatile(plan)
    golden_cmp = _strip_volatile(golden)

    plan_json = serialize(plan_cmp)
    golden_json = serialize(golden_cmp)

    if plan_json == golden_json:
        return True, ""

    # Find first differing line for diagnostics
    plan_lines = plan_json.splitlines()
    golden_lines = golden_json.splitlines()
    for i, (p, g) in enumerate(zip(plan_lines, golden_lines), 1):
        if p != g:
            return False, (
                f"Line {i} differs:\n"
                f"  got:      {p.strip()}\n"
                f"  expected: {g.strip()}"
            )

    # Length difference
    if len(plan_lines) != len(golden_lines):
        return False, (
            f"Line count differs: got {len(plan_lines)}, "
            f"expected {len(golden_lines)}"
        )

    return False, "Unknown difference"


def _strip_volatile(data: dict[str, Any]) -> dict[str, Any]:
    """Remove volatile fields that shouldn't affect comparison."""
    out = json.loads(json.dumps(data))  # deep copy
    meta = out.get("metadata", {})
    meta.pop("generated_at", None)
    return out
