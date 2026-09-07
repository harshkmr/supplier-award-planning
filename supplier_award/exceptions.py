"""Custom exceptions for the supplier_award package."""


class SupplierAwardError(Exception):
    """Base exception for all supplier_award errors."""


class ConfigValidationError(SupplierAwardError):
    """Raised when a YAML configuration fails validation.

    Examples: missing required fields, invalid container type,
    zero/negative weights or costs, unrecognised currency codes.
    """


class OverweightError(SupplierAwardError):
    """Raised when a supplier's allocation exceeds ISO container limits.

    The ISO maximum gross weights are:
      - 20ft TEU: 30,480 kg
      - 40ft FEU: 34,000 kg
    """


class InvalidSupplierError(SupplierAwardError):
    """Raised when a supplier record is incomplete or inconsistent.

    Examples: missing weight_per_unit_kg, zero units_offered,
    or a currency not in the supported set (EUR, GBP, USD).
    """


class FXFetchError(SupplierAwardError):
    """Raised when FX rates cannot be obtained from the network or cache.

    This covers HTTP errors from the Frankfurter.app API as well as
    the case where no cache file exists and the network is unavailable.
    """


class StaleRatesError(SupplierAwardError):
    """Raised when cached FX rates are older than the staleness threshold.

    The default staleness threshold is 24 hours, configurable via
    the ``staleness_hours`` field in the YAML configuration.
    """
