"""Tests for the _container_util C extension."""

import pytest

from supplier_award._container_util import score_utilization


class TestScoreUtilizationNormal:
    """Normal-case tests with known values from worked examples."""

    def test_full_utilization(self):
        """Cargo exactly fills payload capacity → 1.0."""
        # max_payload = 30480 - 2200 = 28280
        result = score_utilization(28280.0, 2200.0, 30480.0)
        assert result == pytest.approx(1.0)

    def test_half_utilization(self):
        """Cargo fills half the payload → 0.5."""
        result = score_utilization(14140.0, 2200.0, 30480.0)
        assert result == pytest.approx(0.5)

    def test_empty_container(self):
        """Zero cargo → 0.0."""
        result = score_utilization(0.0, 2200.0, 30480.0)
        assert result == pytest.approx(0.0)

    def test_20ft_realistic(self):
        """Realistic 20ft TEU: 12,000 kg cargo in a 28,280 kg payload container."""
        result = score_utilization(12000.0, 2200.0, 30480.0)
        expected = 12000.0 / 28280.0  # ≈ 0.4243
        assert result == pytest.approx(expected, rel=1e-9)

    def test_40ft_realistic(self):
        """Realistic 40ft FEU: 25,000 kg cargo in a 30,200 kg payload container."""
        result = score_utilization(25000.0, 3800.0, 34000.0)
        expected = 25000.0 / 30200.0  # ≈ 0.8278
        assert result == pytest.approx(expected, rel=1e-9)

    def test_small_cargo(self):
        """Very small cargo → small utilization."""
        result = score_utilization(1.0, 2200.0, 30480.0)
        expected = 1.0 / 28280.0
        assert result == pytest.approx(expected, rel=1e-9)


class TestScoreUtilizationErrors:
    """Error-case tests: ValueError and OverflowError."""

    def test_negative_cargo(self):
        """Negative cargo weight → ValueError."""
        with pytest.raises(ValueError, match="cargo_weight_kg must be non-negative"):
            score_utilization(-1.0, 2200.0, 30480.0)

    def test_negative_tare(self):
        """Negative tare weight → ValueError."""
        with pytest.raises(ValueError, match="tare_weight_kg must be non-negative"):
            score_utilization(1000.0, -1.0, 30480.0)

    def test_negative_max_gross(self):
        """Negative max gross → ValueError."""
        with pytest.raises(ValueError, match="max_gross_kg must be non-negative"):
            score_utilization(1000.0, 2200.0, -1.0)

    def test_max_gross_equals_tare(self):
        """max_gross == tare → zero payload → ValueError."""
        with pytest.raises(ValueError, match="max_gross_kg must be greater than tare"):
            score_utilization(1000.0, 5000.0, 5000.0)

    def test_max_gross_less_than_tare(self):
        """max_gross < tare → negative payload → ValueError."""
        with pytest.raises(ValueError, match="max_gross_kg must be greater than tare"):
            score_utilization(1000.0, 5000.0, 3000.0)

    def test_overweight_cargo(self):
        """Cargo exceeds payload → OverflowError."""
        # payload = 30480 - 2200 = 28280, cargo = 30000 > 28280
        with pytest.raises(OverflowError, match="cargo exceeds container payload"):
            score_utilization(30000.0, 2200.0, 30480.0)

    def test_wrong_arg_count(self):
        """Too few arguments → TypeError."""
        with pytest.raises(TypeError):
            score_utilization(1000.0, 2200.0)

    def test_wrong_arg_type(self):
        """Non-numeric argument → TypeError."""
        with pytest.raises(TypeError):
            score_utilization("abc", 2200.0, 30480.0)
