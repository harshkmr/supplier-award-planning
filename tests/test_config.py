"""Tests for the YAML configuration loader."""

import pytest
import yaml

from supplier_award.config import load_config, CONTAINER_SPECS
from supplier_award.exceptions import ConfigValidationError, OverweightError


class TestLoadConfigValid:
    """Tests that valid configurations load correctly."""

    def test_load_sample_config(self, sample_config_path):
        """The checked-in sample config loads without error."""
        config = load_config(sample_config_path)
        assert config["base_currency"] == "EUR"
        assert config["container_type"] == "20ft"
        assert len(config["suppliers"]) == 3

    def test_supplier_fields_present(self, sample_config_path):
        """Every supplier has all required fields."""
        config = load_config(sample_config_path)
        for s in config["suppliers"]:
            assert "name" in s
            assert "currency" in s
            assert "unit_cost" in s
            assert "weight_per_unit_kg" in s
            assert "units_offered" in s

    def test_staleness_default(self, valid_config_yaml):
        """staleness_hours defaults to 24.0 when omitted."""
        config = load_config(valid_config_yaml)
        assert config["staleness_hours"] == 24.0

    def test_40ft_container(self, tmp_path):
        """A 40ft container type is accepted."""
        cfg = tmp_path / "c.yaml"
        cfg.write_text(
            """
base_currency: USD
container_type: 40ft
suppliers:
  - name: X
    currency: USD
    unit_cost: 5
    weight_per_unit_kg: 1.0
    units_offered: 10
""",
            encoding="utf-8",
        )
        config = load_config(cfg)
        assert config["container_type"] == "40ft"


class TestLoadConfigRejections:
    """Tests that invalid configurations are rejected with clear errors."""

    def test_missing_file(self):
        """Non-existent file → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_non_mapping_yaml(self, tmp_path):
        """A YAML list instead of mapping → ConfigValidationError."""
        cfg = tmp_path / "list.yaml"
        cfg.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ConfigValidationError, match="YAML mapping"):
            load_config(cfg)

    def test_missing_base_currency(self, tmp_path):
        """Missing base_currency → ConfigValidationError."""
        cfg = tmp_path / "c.yaml"
        cfg.write_text(
            """
container_type: 20ft
suppliers:
  - name: X
    currency: EUR
    unit_cost: 1
    weight_per_unit_kg: 1.0
    units_offered: 1
""",
            encoding="utf-8",
        )
        with pytest.raises(ConfigValidationError, match="base_currency"):
            load_config(cfg)

    def test_invalid_container_type(self, tmp_path):
        """Unknown container type → ConfigValidationError."""
        cfg = tmp_path / "c.yaml"
        cfg.write_text(
            """
base_currency: EUR
container_type: 50ft
suppliers:
  - name: X
    currency: EUR
    unit_cost: 1
    weight_per_unit_kg: 1.0
    units_offered: 1
""",
            encoding="utf-8",
        )
        with pytest.raises(ConfigValidationError, match="container_type"):
            load_config(cfg)

    def test_invalid_currency(self, tmp_path):
        """Unsupported currency code → ConfigValidationError."""
        cfg = tmp_path / "c.yaml"
        cfg.write_text(
            """
base_currency: EUR
container_type: 20ft
suppliers:
  - name: X
    currency: JPY
    unit_cost: 1
    weight_per_unit_kg: 1.0
    units_offered: 1
""",
            encoding="utf-8",
        )
        with pytest.raises(ConfigValidationError, match="currency"):
            load_config(cfg)

    def test_zero_weight(self, tmp_path):
        """Zero weight_per_unit_kg → ConfigValidationError."""
        cfg = tmp_path / "c.yaml"
        cfg.write_text(
            """
base_currency: EUR
container_type: 20ft
suppliers:
  - name: X
    currency: EUR
    unit_cost: 1
    weight_per_unit_kg: 0
    units_offered: 1
""",
            encoding="utf-8",
        )
        with pytest.raises(ConfigValidationError, match="weight_per_unit_kg"):
            load_config(cfg)

    def test_negative_cost(self, tmp_path):
        """Negative unit_cost → ConfigValidationError."""
        cfg = tmp_path / "c.yaml"
        cfg.write_text(
            """
base_currency: EUR
container_type: 20ft
suppliers:
  - name: X
    currency: EUR
    unit_cost: -5
    weight_per_unit_kg: 1.0
    units_offered: 1
""",
            encoding="utf-8",
        )
        with pytest.raises(ConfigValidationError, match="unit_cost"):
            load_config(cfg)

    def test_missing_weight_field(self, bad_config_dir):
        """Config with missing weight_per_unit_kg → ConfigValidationError."""
        with pytest.raises(ConfigValidationError, match="weight_per_unit_kg"):
            load_config(bad_config_dir / "missing_weight.yaml")

    def test_overweight_supplier(self, bad_config_dir):
        """Single unit exceeding container payload → OverweightError."""
        with pytest.raises(OverweightError, match="exceeds"):
            load_config(bad_config_dir / "overweight.yaml")

    def test_empty_suppliers(self, tmp_path):
        """Empty suppliers list → ConfigValidationError."""
        cfg = tmp_path / "c.yaml"
        cfg.write_text(
            """
base_currency: EUR
container_type: 20ft
suppliers: []
""",
            encoding="utf-8",
        )
        with pytest.raises(ConfigValidationError, match="non-empty"):
            load_config(cfg)


class TestSafeYamlOnly:
    """Verify that only yaml.safe_load() is used."""

    def test_unsafe_yaml_rejected(self, bad_config_dir):
        """YAML with Python tags is rejected by safe_load."""
        # yaml.safe_load raises ConstructorError for !!python tags
        with pytest.raises(yaml.YAMLError):
            load_config(bad_config_dir / "unsafe_yaml.yaml")

    def test_no_yaml_load_in_source(self):
        """The config module source code never calls yaml.load()."""
        import ast
        import inspect
        from supplier_award import config as config_mod

        source = inspect.getsource(config_mod)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                # Check for yaml.load(...) call pattern
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "load"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "yaml"
                ):
                    pytest.fail(
                        f"Line {node.lineno}: found unsafe yaml.load() call"
                    )
