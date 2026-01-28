"""Tests for config module."""

import pytest
from pathlib import Path
from yolo_cage.config import load_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_empty_config(self, tmp_path):
        """Empty config returns empty dict."""
        config_path = tmp_path / "config.env"
        config_path.write_text("")
        result = load_config(config_path)
        assert result == {}

    def test_load_nonexistent_config(self, tmp_path):
        """Missing config returns empty dict."""
        config_path = tmp_path / "config.env"
        result = load_config(config_path)
        assert result == {}

    def test_load_simple_config(self, tmp_path):
        """Load simple key=value pairs."""
        config_path = tmp_path / "config.env"
        config_path.write_text("KEY=value\nKEY2=value2\n")
        result = load_config(config_path)
        assert result == {"KEY": "value", "KEY2": "value2"}

    def test_skip_comments(self, tmp_path):
        """Comments are skipped."""
        config_path = tmp_path / "config.env"
        config_path.write_text("# comment\nKEY=value\n")
        result = load_config(config_path)
        assert result == {"KEY": "value"}

    def test_skip_empty_lines(self, tmp_path):
        """Empty lines are skipped."""
        config_path = tmp_path / "config.env"
        config_path.write_text("KEY=value\n\nKEY2=value2\n")
        result = load_config(config_path)
        assert result == {"KEY": "value", "KEY2": "value2"}

    def test_handle_values_with_equals(self, tmp_path):
        """Values containing = are handled correctly."""
        config_path = tmp_path / "config.env"
        config_path.write_text("KEY=value=with=equals\n")
        result = load_config(config_path)
        assert result == {"KEY": "value=with=equals"}

    def test_strip_whitespace(self, tmp_path):
        """Whitespace is stripped from keys and values."""
        config_path = tmp_path / "config.env"
        config_path.write_text("  KEY  =  value  \n")
        result = load_config(config_path)
        assert result == {"KEY": "value"}
