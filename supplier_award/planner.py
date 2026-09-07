"""Award planner engine.

Loads config, fetches FX rates, normalises costs, computes container
utilization via the C extension, and ranks suppliers by effective cost.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from supplier_award._container_util import score_utilization
from supplier_award.config import CONTAINER_SPECS, load_config
from supplier_award.exceptions import OverweightError
from supplier_award.fx import fetch_rates


def plan(
    config_path: str | Path,
    cache_dir: str | Path | None = None,
    fx_rates: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Generate a ranked award plan from a YAML configuration.

    Args:
        config_path: Path to the YAML configuration file.
        cache_dir: Optional override for the FX cache directory.
        fx_rates: Optional pre-fetched FX rates dict.  When provided
            the planner skips the live/cached fetch — useful for
            deterministic testing with pinned rates.

    Returns:
        Award plan dictionary with ``metadata`` and ``awards`` keys.
        Awards are ranked by effective cost (ascending — lower is better).

    Raises:
        ConfigValidationError: If the configuration is invalid.
        FXFetchError / StaleRatesError: If FX rates are unavailable.
        OverweightError: If a supplier's allocation exceeds limits.
    """
    config = load_config(config_path)
    base_currency = config["base_currency"]
    container_type = config["container_type"]
    container = CONTAINER_SPECS[container_type]
    staleness_hours = config.get("staleness_hours", 24.0)

    # Determine which currencies we need to convert
    supplier_currencies = {
        s["currency"] for s in config["suppliers"]
    }
    needed_quotes = sorted(supplier_currencies - {base_currency})

    # Fetch or use provided FX rates
    if fx_rates is None:
        rates = fetch_rates(
            base=base_currency,
            quotes=needed_quotes,
            staleness_hours=staleness_hours,
            cache_dir=cache_dir,
        )
    else:
        rates = fx_rates

    # Score each supplier
    awards: list[dict[str, Any]] = []
    tare_kg = container["tare_kg"]
    max_gross_kg = container["max_gross_kg"]
    max_payload_kg = container["max_payload_kg"]

    for supplier in config["suppliers"]:
        name = supplier["name"]
        currency = supplier["currency"]
        unit_cost = supplier["unit_cost"]
        weight_per_unit = supplier["weight_per_unit_kg"]

        # Normalise cost to base currency
        rate = rates.get(currency)
        if rate is None or rate == 0:
            raise ValueError(
                f"No FX rate for {currency} → {base_currency}"
            )
        # If base is EUR and supplier quotes GBP, rate is EUR-per-GBP.
        # cost_in_base = cost_in_supplier_currency / rate_of_base_per_supplier
        # Actually: Frankfurter gives rates FROM base.  So rate for GBP
        # means 1 EUR = rate GBP.  To convert GBP price to EUR:
        # cost_eur = cost_gbp / rate_gbp
        if currency == base_currency:
            normalized_cost = float(unit_cost)
        else:
            normalized_cost = float(unit_cost) / rate

        # Container utilization
        max_units = math.floor(max_payload_kg / weight_per_unit)
        if max_units < 1:
            raise OverweightError(
                f"Supplier '{name}': a single unit weighs {weight_per_unit} kg "
                f"but container payload is only {max_payload_kg} kg"
            )

        cargo_weight = max_units * weight_per_unit
        utilization = score_utilization(cargo_weight, tare_kg, max_gross_kg)

        effective_cost = normalized_cost / utilization if utilization > 0 else float("inf")

        awards.append({
            "supplier": name,
            "currency": currency,
            "unit_cost": unit_cost,
            "normalized_cost": round(normalized_cost, 4),
            "weight_per_unit_kg": weight_per_unit,
            "max_units_per_container": max_units,
            "utilization": round(utilization, 4),
            "effective_cost": round(effective_cost, 4),
        })

    # Rank by effective cost ascending
    awards.sort(key=lambda a: a["effective_cost"])
    for rank, award in enumerate(awards, 1):
        award["rank"] = rank

    # Build FX rates for metadata (only include the rates we used)
    fx_meta = {
        k: round(v, 6) for k, v in rates.items() if k != base_currency
    }

    return {
        "metadata": {
            "base_currency": base_currency,
            "container_type": container_type,
            "fx_rates": fx_meta,
        },
        "awards": awards,
    }
