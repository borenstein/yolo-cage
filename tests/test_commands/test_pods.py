"""Tests for pod commands."""

import argparse
import pytest
from unittest.mock import patch, MagicMock

from yolo_cage.commands.pods import cmd_list, cmd_create


class TestPodCommands:
    """Tests for pod commands."""

    def test_list_requires_running_vm(self, instance_with_config, mocker):
        """List command exits if VM is not running."""
        # Mock get_vm_status at the vm module level where ensure_vm_running uses it
        mocker.patch("yolo_cage.vm.get_vm_status", return_value="poweroff")

        args = argparse.Namespace(instance=None)

        with pytest.raises(SystemExit):
            cmd_list(args)

    def test_create_validates_repo_access(self, instance_with_config, mocker):
        """Create command validates repository access."""
        mocker.patch("yolo_cage.vm.get_vm_status", return_value="running")
        mocker.patch(
            "yolo_cage.commands.pods.validate_github_repo",
            return_value=(False, "Access denied"),
        )

        args = argparse.Namespace(instance=None, branch="test-branch")

        with pytest.raises(SystemExit):
            cmd_create(args)

    def test_create_calls_inner_command(self, instance_with_config, mocker):
        """Create command calls yolo-cage-inner create."""
        mocker.patch("yolo_cage.vm.get_vm_status", return_value="running")
        mocker.patch(
            "yolo_cage.commands.pods.validate_github_repo",
            return_value=(True, "OK"),
        )
        mock_ssh = mocker.patch("yolo_cage.commands.pods.vagrant_ssh")

        args = argparse.Namespace(instance=None, branch="test-branch")

        cmd_create(args)

        mock_ssh.assert_called_once()
        call_args = mock_ssh.call_args
        assert "yolo-cage-inner create 'test-branch'" in call_args[0][1]
