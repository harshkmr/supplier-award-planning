"""CLI entry point for supplier_award.

Usage::

    python -m supplier_award plan config.yaml
    supplier-award plan config.yaml
"""

from __future__ import annotations

import argparse
import json
import sys

from supplier_award.exceptions import SupplierAwardError
from supplier_award.golden import serialize
from supplier_award.planner import plan


def main(argv: list[str] | None = None) -> int:
    """CLI main entry point.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code: 0 on success, 1 on handled error, 2 on usage error.
    """
    parser = argparse.ArgumentParser(
        prog="supplier-award",
        description="Supplier award planning with ISO container limits and live FX rates.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # plan subcommand
    plan_parser = subparsers.add_parser(
        "plan",
        help="Generate an award plan from a YAML configuration.",
    )
    plan_parser.add_argument(
        "config",
        help="Path to the YAML configuration file.",
    )
    plan_parser.add_argument(
        "--cache-dir",
        default=None,
        help="Directory for FX rate cache (default: ~/.supplier_award/).",
    )
    plan_parser.add_argument(
        "--golden",
        default=None,
        help="Path to a golden JSON file for comparison.",
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 2

    if args.command == "plan":
        return _run_plan(args)

    return 0


def _run_plan(args: argparse.Namespace) -> int:
    """Execute the plan subcommand."""
    try:
        result = plan(args.config, cache_dir=args.cache_dir)
    except SupplierAwardError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Output the plan
    print(serialize(result), end="")

    # Golden file comparison if requested
    if args.golden:
        from supplier_award.golden import compare

        match, detail = compare(result, args.golden)
        if match:
            print("✓ Output matches golden file.", file=sys.stderr)
        else:
            print(f"✗ Golden file mismatch:\n{detail}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
