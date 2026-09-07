"""Tests for the FX rate fetcher."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from supplier_award.exceptions import FXFetchError, StaleRatesError
from supplier_award.fx import fetch_rates


class TestFetchRatesLive:
    """Tests with mocked HTTP responses."""

    @patch("supplier_award.fx.requests.get")
    def test_successful_fetch(self, mock_get, tmp_cache_dir, mock_fx_response):
        """Successful API call returns rates and caches them."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_fx_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        rates = fetch_rates("EUR", ["GBP", "USD"], cache_dir=tmp_cache_dir)

        assert rates["EUR"] == 1.0
        assert rates["GBP"] == pytest.approx(0.856)
        assert rates["USD"] == pytest.approx(1.085)

        # Verify cache was written
        cache_file = tmp_cache_dir / "fx_cache.json"
        assert cache_file.is_file()

    @patch("supplier_award.fx.requests.get")
    def test_base_currency_always_one(self, mock_get, tmp_cache_dir, mock_fx_response):
        """Base currency rate is always 1.0."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_fx_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        rates = fetch_rates("EUR", ["GBP"], cache_dir=tmp_cache_dir)
        assert rates["EUR"] == 1.0

    @patch("supplier_award.fx.requests.get")
    def test_api_params_correct(self, mock_get, tmp_cache_dir, mock_fx_response):
        """API is called with correct base and quotes parameters."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_fx_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        fetch_rates("EUR", ["GBP", "USD"], cache_dir=tmp_cache_dir)

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"]["base"] == "EUR"
        assert "GBP" in call_kwargs[1]["params"]["quotes"]
        assert "USD" in call_kwargs[1]["params"]["quotes"]


class TestFetchRatesFallback:
    """Tests for cache fallback behavior."""

    @patch("supplier_award.fx.requests.get")
    def test_network_error_uses_cache(self, mock_get, tmp_cache_dir):
        """Network failure falls back to fresh cache."""
        # Pre-populate cache
        cache_file = tmp_cache_dir / "fx_cache.json"
        cache_data = {
            "base": "EUR",
            "rates": {"EUR": 1.0, "GBP": 0.85, "USD": 1.10},
            "timestamp": time.time(),  # fresh
        }
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

        # Simulate network error
        mock_get.side_effect = requests.ConnectionError("no network")

        rates = fetch_rates("EUR", ["GBP", "USD"], cache_dir=tmp_cache_dir)
        assert rates["GBP"] == pytest.approx(0.85)
        assert rates["USD"] == pytest.approx(1.10)

    @patch("supplier_award.fx.requests.get")
    def test_network_error_no_cache_raises(self, mock_get, tmp_cache_dir):
        """Network failure with no cache → FXFetchError."""
        mock_get.side_effect = requests.ConnectionError("no network")

        with pytest.raises(FXFetchError, match="no cache"):
            fetch_rates("EUR", ["GBP"], cache_dir=tmp_cache_dir)

    @patch("supplier_award.fx.requests.get")
    def test_stale_cache_raises(self, mock_get, tmp_cache_dir):
        """Network failure with stale cache → StaleRatesError."""
        # Pre-populate cache with old timestamp
        cache_file = tmp_cache_dir / "fx_cache.json"
        cache_data = {
            "base": "EUR",
            "rates": {"EUR": 1.0, "GBP": 0.85},
            "timestamp": time.time() - (48 * 3600),  # 48 hours ago
        }
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

        mock_get.side_effect = requests.ConnectionError("no network")

        with pytest.raises(StaleRatesError, match="staleness threshold"):
            fetch_rates(
                "EUR", ["GBP"], staleness_hours=24, cache_dir=tmp_cache_dir
            )

    @patch("supplier_award.fx.requests.get")
    def test_http_error_falls_back(self, mock_get, tmp_cache_dir):
        """HTTP 500 error falls back to fresh cache."""
        # Pre-populate cache
        cache_file = tmp_cache_dir / "fx_cache.json"
        cache_data = {
            "base": "EUR",
            "rates": {"EUR": 1.0, "GBP": 0.86},
            "timestamp": time.time(),
        }
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

        # Simulate HTTP 500
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp
        )
        mock_get.return_value = mock_resp

        rates = fetch_rates("EUR", ["GBP"], cache_dir=tmp_cache_dir)
        assert rates["GBP"] == pytest.approx(0.86)


class TestCacheIntegrity:
    """Tests for cache read/write correctness."""

    @patch("supplier_award.fx.requests.get")
    def test_cache_base_mismatch_ignored(self, mock_get, tmp_cache_dir):
        """Cache with wrong base currency is treated as missing."""
        # Cache for USD, but we request EUR
        cache_file = tmp_cache_dir / "fx_cache.json"
        cache_data = {
            "base": "USD",
            "rates": {"USD": 1.0, "GBP": 0.75},
            "timestamp": time.time(),
        }
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

        mock_get.side_effect = requests.ConnectionError("no network")

        with pytest.raises(FXFetchError, match="no cache"):
            fetch_rates("EUR", ["GBP"], cache_dir=tmp_cache_dir)
