"""Shared pytest fixtures for supplier_award tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# Project root — tests/ is one level below
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_CONFIG = DATA_DIR / "sample_config.yaml"
BAD_CONFIGS_DIR = DATA_DIR / "bad_configs"

# Pinned FX rates for deterministic testing
PINNED_FX_RATES = {
    "EUR": 1.0,
    "GBP": 0.8560,
    "USD": 1.0850,
}


@pytest.fixture
def sample_config_path() -> Path:
    """Path to the valid sample configuration."""
    return SAMPLE_CONFIG


@pytest.fixture
def bad_config_dir() -> Path:
    """Path to the directory of invalid configurations."""
    return BAD_CONFIGS_DIR


@pytest.fixture
def pinned_fx_rates() -> dict[str, float]:
    """Deterministic FX rates for testing."""
    return PINNED_FX_RATES.copy()


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> Path:
    """Temporary directory for FX cache files."""
    cache_dir = tmp_path / "fx_cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def mock_fx_response() -> dict:
    """Mock Frankfurter.app v2 API response."""
    return {
        "date": "2025-01-15",
        "base": "EUR",
        "rates": {
            "GBP": 0.8560,
            "USD": 1.0850,
        },
    }


@pytest.fixture
def valid_config_yaml(tmp_path: Path) -> Path:
    """Create a minimal valid config in a temp directory."""
    config = tmp_path / "config.yaml"
    config.write_text(
        """
base_currency: EUR
staleness_hours: 24
container_type: 20ft
suppliers:
  - name: "TestSupplier"
    currency: EUR
    unit_cost: 10.0
    weight_per_unit_kg: 1.0
    units_offered: 100
""",
        encoding="utf-8",
    )
    return config
