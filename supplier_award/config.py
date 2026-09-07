"""Configuration loader for supplier award planning.

Loads YAML configurations using ``yaml.safe_load()`` only (never
``yaml.load()``), validates all fields, and rejects insecure or
incomplete inputs at load time.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

from supplier_award.exceptions import ConfigValidationError, OverweightError

# ISO 668 / ISO 1496-1 container specifications
CONTAINER_SPECS: dict[str, dict[str, float]] = {
    "20ft": {
        "tare_kg": 2200.0,
        "max_gross_kg": 30480.0,
        "max_payload_kg": 28280.0,
    },
    "40ft": {
        "tare_kg": 3800.0,
        "max_gross_kg": 34000.0,
        "max_payload_kg": 30200.0,
    },
}

SUPPORTED_CURRENCIES = {"EUR", "GBP", "USD"}

REQUIRED_SUPPLIER_FIELDS = {
    "name": str,
    "currency": str,
    "unit_cost": (int, float),
    "weight_per_unit_kg": (int, float),
    "units_offered": int,
}


def load_config(path: str | Path) -> dict[str, Any]:
    """Load and validate a supplier award configuration from YAML.

    Uses ``yaml.safe_load()`` exclusively — arbitrary code execution
    via YAML deserialization is impossible.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Validated configuration dictionary with normalised types.

    Raises:
        ConfigValidationError: If any field is missing, has the wrong type,
            or has an invalid value.
        OverweightError: If any supplier's per-unit weight would exceed
            the container's payload capacity (i.e., not even one unit fits).
        FileNotFoundError: If the config file does not exist.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigValidationError(
            f"Invalid or unsafe YAML in {path}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise ConfigValidationError(
            f"Config must be a YAML mapping, got {type(raw).__name__}"
        )

    _validate_top_level(raw)
    _validate_suppliers(raw)

    return raw


def _validate_top_level(config: dict[str, Any]) -> None:
    """Validate top-level configuration fields."""
    # base_currency
    base = config.get("base_currency")
    if base is None:
        raise ConfigValidationError("Missing required field: base_currency")
    if base not in SUPPORTED_CURRENCIES:
        raise ConfigValidationError(
            f"base_currency must be one of {SUPPORTED_CURRENCIES}, got '{base}'"
        )

    # container_type
    ctype = config.get("container_type")
    if ctype is None:
        raise ConfigValidationError("Missing required field: container_type")
    if ctype not in CONTAINER_SPECS:
        raise ConfigValidationError(
            f"container_type must be one of {set(CONTAINER_SPECS.keys())}, "
            f"got '{ctype}'"
        )

    # staleness_hours (optional, default 24)
    staleness = config.get("staleness_hours", 24)
    if not isinstance(staleness, (int, float)) or staleness <= 0:
        raise ConfigValidationError(
            f"staleness_hours must be a positive number, got {staleness!r}"
        )
    config["staleness_hours"] = float(staleness)

    # suppliers list
    suppliers = config.get("suppliers")
    if suppliers is None:
        raise ConfigValidationError("Missing required field: suppliers")
    if not isinstance(suppliers, list) or len(suppliers) == 0:
        raise ConfigValidationError("suppliers must be a non-empty list")


def _validate_suppliers(config: dict[str, Any]) -> None:
    """Validate each supplier entry and check container weight limits."""
    container_spec = CONTAINER_SPECS[config["container_type"]]
    max_payload = container_spec["max_payload_kg"]

    for i, supplier in enumerate(config["suppliers"]):
        prefix = f"suppliers[{i}]"

        if not isinstance(supplier, dict):
            raise ConfigValidationError(
                f"{prefix} must be a mapping, got {type(supplier).__name__}"
            )

        # Check required fields and types
        for field, expected_type in REQUIRED_SUPPLIER_FIELDS.items():
            value = supplier.get(field)
            if value is None:
                raise ConfigValidationError(
                    f"{prefix}: missing required field '{field}'"
                )
            if not isinstance(value, expected_type):
                raise ConfigValidationError(
                    f"{prefix}.{field}: expected {expected_type}, "
                    f"got {type(value).__name__}"
                )

        # Validate currency
        currency = supplier["currency"]
        if currency not in SUPPORTED_CURRENCIES:
            raise ConfigValidationError(
                f"{prefix}.currency: must be one of {SUPPORTED_CURRENCIES}, "
                f"got '{currency}'"
            )

        # Validate positive values
        if supplier["unit_cost"] <= 0:
            raise ConfigValidationError(
                f"{prefix}.unit_cost: must be positive, "
                f"got {supplier['unit_cost']}"
            )
        if supplier["weight_per_unit_kg"] <= 0:
            raise ConfigValidationError(
                f"{prefix}.weight_per_unit_kg: must be positive, "
                f"got {supplier['weight_per_unit_kg']}"
            )
        if supplier["units_offered"] <= 0:
            raise ConfigValidationError(
                f"{prefix}.units_offered: must be positive, "
                f"got {supplier['units_offered']}"
            )

        # Check that at least one unit fits in the container
        weight_per_unit = supplier["weight_per_unit_kg"]
        max_units = math.floor(max_payload / weight_per_unit)
        if max_units < 1:
            raise OverweightError(
                f"{prefix} ('{supplier['name']}'): a single unit weighs "
                f"{weight_per_unit} kg, which exceeds the {config['container_type']} "
                f"container payload capacity of {max_payload} kg"
            )
