"""Tests for the golden file comparison utility."""

import json
from pathlib import Path

import pytest

from supplier_award.golden import compare, serialize
from supplier_award.planner import plan


PINNED_RATES = {"EUR": 1.0, "GBP": 0.856, "USD": 1.085}


class TestSerialize:
    """Test deterministic JSON serialization."""

    def test_sorted_keys(self):
        """Output has sorted keys."""
        data = {"z": 1, "a": 2, "m": 3}
        result = serialize(data)
        keys_in_order = [k.strip().strip('"') for k in result.split("\n") if ":" in k]
        assert keys_in_order == sorted(keys_in_order)

    def test_trailing_newline(self):
        """Output ends with a newline."""
        assert serialize({}).endswith("\n")

    def test_deterministic(self):
        """Same input always produces same output."""
        data = {"b": 2, "a": 1, "c": [3, 2, 1]}
        assert serialize(data) == serialize(data)


class TestCompare:
    """Test golden file comparison."""

    def test_matching_plan(self, sample_config_path, tmp_path):
        """Plan that matches golden file returns (True, '')."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        golden_path = tmp_path / "golden.json"
        golden_path.write_text(serialize(result), encoding="utf-8")

        match, detail = compare(result, golden_path)
        assert match is True
        assert detail == ""

    def test_mismatched_plan(self, sample_config_path, tmp_path):
        """Modified plan does not match golden file."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        golden_path = tmp_path / "golden.json"
        golden_path.write_text(serialize(result), encoding="utf-8")

        # Modify the result
        result["awards"][0]["effective_cost"] = 999.99

        match, detail = compare(result, golden_path)
        assert match is False
        assert "differs" in detail

    def test_missing_golden_file(self, sample_config_path):
        """Missing golden file → FileNotFoundError."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)
        with pytest.raises(FileNotFoundError):
            compare(result, "/nonexistent/golden.json")

    def test_ignores_generated_at(self, sample_config_path, tmp_path):
        """generated_at in metadata is stripped before comparison."""
        result = plan(sample_config_path, fx_rates=PINNED_RATES)

        # Golden file without generated_at
        golden_path = tmp_path / "golden.json"
        golden_path.write_text(serialize(result), encoding="utf-8")

        # Add generated_at to result — should still match
        result["metadata"]["generated_at"] = "2025-01-15T10:00:00Z"

        match, detail = compare(result, golden_path)
        assert match is True
