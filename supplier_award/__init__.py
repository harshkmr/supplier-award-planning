"""
supplier_award — Harden supplier award planning.

Ranks purchase-order awards across international suppliers by combining
quoted unit costs, ISO shipping container limits, and live FX rates.
"""

__version__ = "0.1.0"

from supplier_award.config import load_config
from supplier_award.fx import fetch_rates
from supplier_award.planner import plan

__all__ = ["load_config", "fetch_rates", "plan", "__version__"]
