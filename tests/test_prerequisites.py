"""Tests for prerequisites module."""

import pytest
import sys
from unittest.mock import patch, MagicMock

from yolo_cage.prerequisites import check_prerequisites


class TestCheckPrerequisites:
    """Tests for check_prerequisites function."""

    def test_all_present_linux(self, monkeypatch):
        """No error when all prerequisites are present on Linux."""
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

                # Should not raise
                check_prerequisites()

    def test_missing_vagrant(self, monkeypatch, capsys):
        """Exits when vagrant is missing."""
        monkeypatch.setattr(sys, "platform", "linux")

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "git": "/usr/bin/git",
                "libvirtd": "/usr/bin/libvirtd",
            }.get(cmd)

            with pytest.raises(SystemExit) as exc_info:
                check_prerequisites()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "vagrant" in captured.out

    def test_missing_git(self, monkeypatch, capsys):
        """Exits when git is missing."""
        monkeypatch.setattr(sys, "platform", "linux")

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "vagrant": "/usr/bin/vagrant",
                "libvirtd": "/usr/bin/libvirtd",
            }.get(cmd)

            with pytest.raises(SystemExit) as exc_info:
                check_prerequisites()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "git" in captured.out

    def test_macos_checks_qemu(self, monkeypatch, capsys):
        """On macOS, checks for QEMU and vagrant-qemu plugin."""
        monkeypatch.setattr(sys, "platform", "darwin")

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: {
                "vagrant": "/usr/local/bin/vagrant",
                "git": "/usr/bin/git",
            }.get(cmd)

            with patch("subprocess.run") as mock_run:
                # brew list doesn't include qemu
                mock_run.side_effect = [
                    MagicMock(returncode=0, stdout="some-other-formula"),
                    MagicMock(returncode=0, stdout=""),  # no vagrant-qemu
                ]

                with pytest.raises(SystemExit):
                    check_prerequisites()

                captured = capsys.readouterr()
                assert "qemu" in captured.out
