"""FX rate fetcher with caching and staleness detection.

Fetches live exchange rates from the Frankfurter.app v2 API, caches
them locally, and falls back to cached rates when the network is
unavailable — with appropriate warnings and errors.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

from supplier_award.exceptions import FXFetchError, StaleRatesError

logger = logging.getLogger(__name__)

_API_BASE = "https://api.frankfurter.dev/v2/rates"
_DEFAULT_CACHE_DIR = Path.home() / ".supplier_award"
_CACHE_FILENAME = "fx_cache.json"


def fetch_rates(
    base: str,
    quotes: list[str],
    staleness_hours: float = 24.0,
    cache_dir: str | Path | None = None,
) -> dict[str, float]:
    """Fetch exchange rates, using cache as fallback.

    Args:
        base: Base currency code (e.g. ``"EUR"``).
        quotes: List of target currency codes (e.g. ``["GBP", "USD"]``).
        staleness_hours: Maximum age of cached rates in hours.
        cache_dir: Directory for the cache file.  Defaults to
            ``~/.supplier_award/``.

    Returns:
        Mapping of currency code → exchange rate relative to *base*.
        The base currency itself is always included with rate 1.0.

    Raises:
        FXFetchError: If rates cannot be obtained from either the
            network or the cache.
        StaleRatesError: If the only available rates are older than
            *staleness_hours*.
    """
    cache_path = _resolve_cache_path(cache_dir)

    # Try live fetch first
    try:
        rates = _fetch_live(base, quotes)
        _write_cache(cache_path, base, rates)
        return rates
    except FXFetchError as live_err:
        logger.warning("Live FX fetch failed: %s — trying cache", live_err)

    # Fall back to cache
    cached = _read_cache(cache_path, base)
    if cached is None:
        raise FXFetchError(
            f"Cannot fetch FX rates from network and no cache exists "
            f"at {cache_path}"
        )

    cache_age_hours = (time.time() - cached["timestamp"]) / 3600.0
    if cache_age_hours > staleness_hours:
        raise StaleRatesError(
            f"Cached FX rates are {cache_age_hours:.1f} hours old, "
            f"exceeding the staleness threshold of {staleness_hours} hours"
        )

    logger.warning(
        "Using cached FX rates (%.1f hours old)", cache_age_hours
    )
    return cached["rates"]


def _fetch_live(base: str, quotes: list[str]) -> dict[str, float]:
    """Fetch rates from the Frankfurter.app v2 API."""
    params = {"base": base, "quotes": ",".join(quotes)}
    try:
        resp = requests.get(_API_BASE, params=params, timeout=10)
        resp.raise_for_status()
    except requests.ConnectionError as exc:
        raise FXFetchError(f"Network error: {exc}") from exc
    except requests.Timeout as exc:
        raise FXFetchError(f"Request timed out: {exc}") from exc
    except requests.HTTPError as exc:
        raise FXFetchError(
            f"HTTP {resp.status_code}: {resp.text}"
        ) from exc

    data = resp.json()
    rates: dict[str, float] = {base: 1.0}

    if isinstance(data, list):
        if not data:
            raise FXFetchError("Empty response from API")
        for item in data:
            if isinstance(item, dict):
                if "quote" in item and "rate" in item:
                    rates[str(item["quote"])] = float(item["rate"])
                elif "rates" in item and isinstance(item["rates"], dict):
                    for q, r in item["rates"].items():
                        rates[str(q)] = float(r)
    elif isinstance(data, dict):
        if "rates" in data and isinstance(data["rates"], dict):
            for q, r in data["rates"].items():
                rates[str(q)] = float(r)
        elif "quote" in data and "rate" in data:
            rates[str(data["quote"])] = float(data["rate"])
    else:
        raise FXFetchError(f"Unexpected API response type: {type(data).__name__}")

    if len(rates) <= 1 and quotes:
        raise FXFetchError(f"No rates found in API response: {data}")

    return rates


def _resolve_cache_path(cache_dir: str | Path | None) -> Path:
    """Resolve the cache file path."""
    directory = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR
    return directory / _CACHE_FILENAME


def _write_cache(
    path: Path, base: str, rates: dict[str, float]
) -> None:
    """Write rates to the cache file with a timestamp."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "base": base,
        "rates": rates,
        "timestamp": time.time(),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)


def _read_cache(path: Path, base: str) -> dict[str, Any] | None:
    """Read cached rates.  Returns None if cache is missing or corrupt."""
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("base") != base:
            logger.warning(
                "Cache base currency mismatch: expected %s, got %s",
                base,
                data.get("base"),
            )
            return None
        return data
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Corrupt cache file %s: %s", path, exc)
        return None
