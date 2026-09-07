"""Tests for the award planner engine."""

import json
import math
from pathlib import Path

import pytest

from supplier_award.planner import plan
from supplier_award.exceptions import OverweightError


# Pinned FX rates — must match conftest.PINNED_FX_RATES
PINNED_RATES = {"EUR": 1.0, "GBP": 0.856, "USD": 1.085}


class TestPlannerRanking:
    """Test that suppliers are ranked correctly by effective cost."""

    def test_plan_returns_awards(self, sample_config_path):
        """The planner returns a non-empty awards list."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        assert "awards" in result
        assert len(result["awards"]) == 3

    def test_awards_ranked_by_effective_cost(self, sample_config_path):
        """Awards are sorted ascending by effective_cost."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        costs = [a["effective_cost"] for a in result["awards"]]
        assert costs == sorted(costs)

    def test_ranks_are_sequential(self, sample_config_path):
        """Rank numbers are 1, 2, 3, …"""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        ranks = [a["rank"] for a in result["awards"]]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_metadata_present(self, sample_config_path):
        """Metadata includes base currency, container type, and FX rates."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        meta = result["metadata"]
        assert meta["base_currency"] == "EUR"
        assert meta["container_type"] == "20ft"
        assert "fx_rates" in meta

    def test_fx_normalization(self, sample_config_path):
        """EUR supplier has normalized_cost == unit_cost."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        eur_award = next(
            a for a in result["awards"] if a["currency"] == "EUR"
        )
        assert eur_award["normalized_cost"] == eur_award["unit_cost"]

    def test_gbp_normalization(self, sample_config_path):
        """GBP cost is normalized: cost_gbp / rate_gbp."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        gbp_award = next(
            a for a in result["awards"] if a["currency"] == "GBP"
        )
        expected = round(11.00 / 0.856, 4)
        assert gbp_award["normalized_cost"] == pytest.approx(expected, rel=1e-3)

    def test_usd_normalization(self, sample_config_path):
        """USD cost is normalized: cost_usd / rate_usd."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        usd_award = next(
            a for a in result["awards"] if a["currency"] == "USD"
        )
        expected = round(14.00 / 1.085, 4)
        assert usd_award["normalized_cost"] == pytest.approx(expected, rel=1e-3)


class TestPlannerContainerLimits:
    """Test that container weight limits are enforced."""

    def test_max_units_per_container(self, sample_config_path):
        """max_units_per_container = floor(payload / weight_per_unit)."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        # 20ft payload = 28280 kg
        for award in result["awards"]:
            expected_max = math.floor(28280.0 / award["weight_per_unit_kg"])
            assert award["max_units_per_container"] == expected_max

    def test_utilization_in_range(self, sample_config_path):
        """All utilization scores are in (0.0, 1.0]."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        for award in result["awards"]:
            assert 0.0 < award["utilization"] <= 1.0

    def test_overweight_rejected(self, bad_config_dir):
        """Config with overweight supplier raises OverweightError."""
        with pytest.raises(OverweightError):
            plan(
                bad_config_dir / "overweight.yaml",
                fx_rates=PINNED_RATES,
            )


class TestPlannerDeterminism:
    """Test that planner output is deterministic."""

    def test_same_input_same_output(self, sample_config_path):
        """Running the planner twice produces identical results."""
        result1 = plan(sample_config_path, fx_rates=PINNED_RATES)
        result2 = plan(sample_config_path, fx_rates=PINNED_RATES)
        assert result1 == result2
