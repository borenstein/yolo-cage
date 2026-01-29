"""Tests for prerequisites module."""

import pytest
import sys
from unittest.mock import patch, MagicMock

from yolo_cage.ops.prerequisites import check_dependencies, format_install_instructions


class TestCheckDependencies:
    """Tests for check_dependencies function."""

    def test_all_present_linux(self, monkeypatch):
        """Returns empty list when all prerequisites are present on Linux."""
        monkeypatch.setattr(sys, "platform", "linux")

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "vagrant": "/usr/bin/vagrant",
                "git": "/usr/bin/git",
                "libvirtd": "/usr/bin/libvirtd",
            }.get(cmd)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="vagrant-libvirt (0.12.0)"
                )

                missing = check_dependencies()
                assert missing == []

    def test_missing_vagrant(self, monkeypatch):
        """Returns vagrant when vagrant is missing."""
        monkeypatch.setattr(sys, "platform", "linux")

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "git": "/usr/bin/git",
                "libvirtd": "/usr/bin/libvirtd",
            }.get(cmd)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="")

                missing = check_dependencies()
                assert "vagrant" in missing

    def test_missing_git(self, monkeypatch):
        """Returns git when git is missing."""
        monkeypatch.setattr(sys, "platform", "linux")

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "vagrant": "/usr/bin/vagrant",
                "libvirtd": "/usr/bin/libvirtd",
            }.get(cmd)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="vagrant-libvirt (0.12.0)"
                )

                missing = check_dependencies()
                assert "git" in missing

    def test_missing_libvirt_on_linux(self, monkeypatch):
        """Returns libvirt when neither libvirt nor VirtualBox present."""
        monkeypatch.setattr(sys, "platform", "linux")

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "vagrant": "/usr/bin/vagrant",
                "git": "/usr/bin/git",
            }.get(cmd)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="")

                missing = check_dependencies()
                assert any("libvirt" in m for m in missing)

    def test_macos_checks_qemu(self, monkeypatch):
        """On macOS, returns qemu when not installed."""
        monkeypatch.setattr(sys, "platform", "darwin")

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "vagrant": "/usr/local/bin/vagrant",
                "git": "/usr/bin/git",
            }.get(cmd)

            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    MagicMock(returncode=0, stdout="some-other-formula"),
                    MagicMock(returncode=0, stdout=""),
                ]

                missing = check_dependencies()
                assert "qemu" in missing

    def test_macos_checks_vagrant_qemu_plugin(self, monkeypatch):
        """On macOS, returns vagrant-qemu plugin when not installed."""
        monkeypatch.setattr(sys, "platform", "darwin")

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "vagrant": "/usr/local/bin/vagrant",
                "git": "/usr/bin/git",
            }.get(cmd)

            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    MagicMock(returncode=0, stdout="qemu"),
                    MagicMock(returncode=0, stdout="some-other-plugin"),
                ]

                missing = check_dependencies()
                assert "vagrant-qemu plugin" in missing


class TestFormatInstallInstructions:
    """Tests for format_install_instructions function."""

    def test_includes_missing_deps(self):
        result = format_install_instructions(["vagrant", "git"])
        assert "vagrant" in result
        assert "git" in result

    def test_includes_install_commands_linux(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        result = format_install_instructions(["vagrant"])
        assert "apt install" in result or "dnf install" in result

    def test_includes_install_commands_macos(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        result = format_install_instructions(["vagrant"])
        assert "brew install" in result
