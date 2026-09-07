#!/usr/bin/env python3
"""Interactive Terminal Demo for Supplier Award Planning.

Demonstrates:
1. Safe YAML loading & rejection of insecure configurations
2. Live FX rates fetched from Frankfurter.app API
3. C extension ISO container payload utilization scoring
4. End-to-end multi-currency supplier award ranking
5. Deterministic Golden JSON comparison
"""

import json
import os
import sys
import time
from pathlib import Path

# Ensure package is importable
sys.path.insert(0, str(Path(__file__).parent))

from supplier_award._container_util import score_utilization
from supplier_award.config import CONTAINER_SPECS, load_config
from supplier_award.exceptions import (
    ConfigValidationError,
    OverweightError,
    SupplierAwardError,
)
from supplier_award.fx import fetch_rates
from supplier_award.golden import compare, serialize
from supplier_award.planner import plan


def print_banner(text: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(step: int, title: str) -> None:
    print(f"\n\033[1;36m[Step {step}] {title}\033[0m")
    print("-" * 60)


def main():
    print_banner("SUPPLIER AWARD PLANNING — HARDENED SYSTEM DEMO")
    print("Languages: Python + C (CPython extension)")
    print("Core: ISO Container Limits + Live Frankfurter.app FX + Safe YAML")
    time.sleep(0.5)

    # -------------------------------------------------------------
    # 1. Insecure vs Safe Configuration Handling
    # -------------------------------------------------------------
    print_section(1, "Security & Validation: Rejecting Insecure YAML")
    print("Attempting to load malicious configuration (data/bad_configs/unsafe_yaml.yaml)...")
    
    try:
        load_config("data/bad_configs/unsafe_yaml.yaml")
        print("\033[31m[FAILED]\033[0m Malicious YAML was not caught!")
    except ConfigValidationError as exc:
        print(f"\033[32m[BLOCKED]\033[0m Caught safely at parse time:")
        print(f"  --> {exc}")

    print("\nAttempting to load overweight allocation (data/bad_configs/overweight.yaml)...")
    try:
        load_config("data/bad_configs/overweight.yaml")
        print("\033[31m[FAILED]\033[0m Overweight config was not caught!")
    except OverweightError as exc:
        print(f"\033[32m[BLOCKED]\033[0m Overweight allocation rejected before processing:")
        print(f"  --> {exc}")

    # -------------------------------------------------------------
    # 2. Live FX API from Frankfurter.app
    # -------------------------------------------------------------
    print_section(2, "Live FX Rates from Frankfurter.app v2 API")
    print("Fetching live market rates for EUR -> GBP, USD...")
    
    try:
        rates = fetch_rates(base="EUR", quotes=["GBP", "USD"], staleness_hours=24)
        for cur, rate in rates.items():
            print(f"  1 EUR = {rate:.4f} {cur}")
    except Exception as exc:
        print(f"  \033[33mWarning: Live fetch failed, using fallback:\033[0m {exc}")
        rates = {"EUR": 1.0, "GBP": 0.856, "USD": 1.085}

    # -------------------------------------------------------------
    # 3. CPython C Extension Container Utilization Scoring
    # -------------------------------------------------------------
    print_section(3, "High-Performance C Extension (_container_util)")
    print("Testing ISO 668 20ft Container (Tare: 2,200 kg | Max Gross: 30,480 kg | Payload: 28,280 kg)")
    
    test_cargos = [0.0, 14140.0, 28280.0]
    for cargo in test_cargos:
        util = score_utilization(cargo, 2200.0, 30480.0)
        pct = util * 100.0
        bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
        print(f"  Cargo: {cargo:8.1f} kg  -->  Utilization: {util:6.4f}  [{bar}] {pct:5.1f}%")

    print("\nTesting C Extension Overflow Safeguard (Cargo: 30,000 kg > 28,280 kg payload):")
    try:
        score_utilization(30000.0, 2200.0, 30480.0)
    except OverflowError as exc:
        print(f"  \033[32m[C GUARDRAIL TRIGGERED]\033[0m {exc}")

    # -------------------------------------------------------------
    # 4. Multi-Currency Award Planning & Ranking
    # -------------------------------------------------------------
    print_section(4, "End-to-End Multi-Currency Award Planning")
    print("Evaluating suppliers from 'data/sample_config.yaml':")
    
    award_plan = plan("data/sample_config.yaml")
    
    print("\n\033[1mRank  Supplier         Quote            Normalized (EUR)  Utilization  Effective Cost\033[0m")
    print("-" * 75)
    for award in award_plan["awards"]:
        quote_str = f"{award['unit_cost']:.2f} {award['currency']}"
        print(
            f" #{award['rank']:<3} {award['supplier']:<16} {quote_str:<16} "
            f"EUR {award['normalized_cost']:<13.4f} "
            f"{award['utilization']*100:5.1f}%       "
            f"EUR {award['effective_cost']:.4f}"
        )

    # -------------------------------------------------------------
    # 5. Golden JSON Verification
    # -------------------------------------------------------------
    print_section(5, "Deterministic Golden JSON Verification")
    pinned_rates = {"EUR": 1.0, "GBP": 0.856, "USD": 1.085}
    pinned_plan = plan("data/sample_config.yaml", fx_rates=pinned_rates)
    
    golden_path = "data/golden/expected_award_plan.json"
    matched, detail = compare(pinned_plan, golden_path)
    if matched:
        print(f"  \033[32m[PASS]\033[0m Pinned plan matches golden file '{golden_path}' exactly.")
    else:
        print(f"  \033[31m[FAIL]\033[0m Golden mismatch: {detail}")

    print_banner("DEMO COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
