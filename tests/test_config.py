"""Tests for Config class."""

import pytest
from pathlib import Path

from yolo_cage.config import Config


class TestConfigLoad:
    """Tests for Config.load()."""

    def test_returns_none_if_missing(self, tmp_path):
        path = tmp_path / "config.env"
        assert Config.load(path) is None

    def test_returns_none_if_missing_pat(self, tmp_path):
        path = tmp_path / "config.env"
        path.write_text("REPO_URL=https://github.com/test/repo\n")
        assert Config.load(path) is None

    def test_returns_none_if_missing_repo(self, tmp_path):
        path = tmp_path / "config.env"
        path.write_text("GITHUB_PAT=ghp_test123\n")
        assert Config.load(path) is None

    def test_loads_required_fields(self, tmp_path):
        path = tmp_path / "config.env"
        path.write_text(
            "GITHUB_PAT=ghp_test123\n"
            "REPO_URL=https://github.com/test/repo\n"
        )
        config = Config.load(path)
        assert config is not None
        assert config.github_pat == "ghp_test123"
        assert config.repo_url == "https://github.com/test/repo"

    def test_loads_optional_fields(self, tmp_path):
        path = tmp_path / "config.env"
        path.write_text(
            "GITHUB_PAT=ghp_test123\n"
            "REPO_URL=https://github.com/test/repo\n"
            "GIT_NAME=Custom Name\n"
            "GIT_EMAIL=custom@example.com\n"
            "PROXY_BYPASS=*.internal\n"
        )
        config = Config.load(path)
        assert config.git_name == "Custom Name"
        assert config.git_email == "custom@example.com"
        assert config.proxy_bypass == "*.internal"

    def test_uses_defaults_for_optional_fields(self, tmp_path):
        path = tmp_path / "config.env"
        path.write_text(
            "GITHUB_PAT=ghp_test123\n"
            "REPO_URL=https://github.com/test/repo\n"
        )
        config = Config.load(path)
        assert config.git_name == "yolo-cage"
        assert config.git_email == "yolo-cage@localhost"
        assert config.proxy_bypass == ""

    def test_ignores_comments_and_blank_lines(self, tmp_path):
        path = tmp_path / "config.env"
        path.write_text(
            "# Comment\n"
            "\n"
            "GITHUB_PAT=ghp_test123\n"
            "# Another comment\n"
            "REPO_URL=https://github.com/test/repo\n"
        )
        config = Config.load(path)
        assert config is not None


class TestConfigSave:
    """Tests for Config.save()."""

    def test_saves_to_file(self, tmp_path):
        path = tmp_path / "config.env"
        config = Config(
            github_pat="ghp_test123",
            repo_url="https://github.com/test/repo",
        )
        config.save(path)

        assert path.exists()
        content = path.read_text()
        assert "GITHUB_PAT=ghp_test123" in content
        assert "REPO_URL=https://github.com/test/repo" in content

    def test_creates_parent_directories(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "config.env"
        config = Config(
            github_pat="ghp_test123",
            repo_url="https://github.com/test/repo",
        )
        config.save(path)
        assert path.exists()

    def test_roundtrip(self, tmp_path):
        """Config can be saved and loaded back."""
        path = tmp_path / "config.env"
        original = Config(
            github_pat="ghp_test123",
            repo_url="https://github.com/test/repo",
            git_name="Test User",
            git_email="test@example.com",
            proxy_bypass="*.internal",
        )
        original.save(path)

        loaded = Config.load(path)
        assert loaded.github_pat == original.github_pat
        assert loaded.repo_url == original.repo_url
        assert loaded.git_name == original.git_name
        assert loaded.git_email == original.git_email
        assert loaded.proxy_bypass == original.proxy_bypass
