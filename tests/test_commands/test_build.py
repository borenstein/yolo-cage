"""Tests for build command."""

import argparse
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from yolo_cage.commands.build import cmd_build
from yolo_cage.instances import (
    list_instances,
    get_default_instance,
    get_instance_config,
    get_repo_dir,
    instance_exists,
)


class TestBuildCommand:
    """Tests for cmd_build function."""

    def test_first_build_creates_default(self, tmp_yolo_home, monkeypatch, mocker):
        """First build without --instance creates 'default' instance."""
        mocker.patch("yolo_cage.commands.build.check_prerequisites")
        mocker.patch("subprocess.run")
        mocker.patch("yolo_cage.commands.build.sync_config_to_vm")
        mocker.patch("yolo_cage.commands.build.detect_local_repo", return_value=None)

        # Don't pre-create instance - let build create it
        # But we need to provide a config file
        config_file = tmp_yolo_home / "test-config.env"
        config_file.write_text("GITHUB_PAT=test\nREPO_URL=https://github.com/test/repo\n")

        args = argparse.Namespace(
            instance=None,
            config_file=str(config_file),
            interactive=False,
            up=False,
        )

        # Mock create_instance to set up the directory structure
        def mock_create_instance(name, repo_path=None):
            instances_dir = tmp_yolo_home / "instances" / name
            instances_dir.mkdir(parents=True, exist_ok=True)
            (instances_dir / "instance.json").write_text('{"repo_path": null}')
            (instances_dir / "repo").mkdir()
            (instances_dir / "repo" / "Vagrantfile").touch()
            return instances_dir

        with patch("yolo_cage.commands.build.create_instance", side_effect=mock_create_instance) as mock_create:
            cmd_build(args)

            # Verify create_instance was called with 'default'
            mock_create.assert_called_once()
            assert mock_create.call_args[0][0] == "default"

    def test_build_errors_if_instance_exists(self, tmp_yolo_home, mocker):
        """Build without --instance errors when instances exist."""
        mocker.patch("yolo_cage.commands.build.check_prerequisites")

        # Create existing instance
        instances_dir = tmp_yolo_home / "instances" / "existing"
        instances_dir.mkdir(parents=True)
        (instances_dir / "instance.json").write_text("{}")

        args = argparse.Namespace(
            instance=None,
            config_file=None,
            interactive=False,
            up=False,
        )

        with pytest.raises(SystemExit):
            cmd_build(args)

    def test_build_with_named_instance(self, tmp_yolo_home, mocker):
        """Build with --instance creates named instance."""
        mocker.patch("yolo_cage.commands.build.check_prerequisites")
        mocker.patch("subprocess.run")
        mocker.patch("yolo_cage.commands.build.sync_config_to_vm")
        mocker.patch("yolo_cage.commands.build.detect_local_repo", return_value=None)

        # Provide a config file
        config_file = tmp_yolo_home / "test-config.env"
        config_file.write_text("GITHUB_PAT=test\nREPO_URL=https://github.com/test/repo\n")

        args = argparse.Namespace(
            instance="myinstance",
            config_file=str(config_file),
            interactive=False,
            up=False,
        )

        # Mock create_instance to set up the directory structure
        def mock_create_instance(name, repo_path=None):
            instances_dir = tmp_yolo_home / "instances" / name
            instances_dir.mkdir(parents=True, exist_ok=True)
            (instances_dir / "instance.json").write_text('{"repo_path": null}')
            (instances_dir / "repo").mkdir()
            (instances_dir / "repo" / "Vagrantfile").touch()
            return instances_dir

        with patch("yolo_cage.commands.build.create_instance", side_effect=mock_create_instance) as mock_create:
            cmd_build(args)

            # Verify create_instance was called with correct name
            mock_create.assert_called_once()
            assert mock_create.call_args[0][0] == "myinstance"

    def test_build_from_local_repo(self, tmp_yolo_home, tmp_repo, mocker):
        """Build from local repo stores repo_path in instance.json."""
        mocker.patch("yolo_cage.commands.build.check_prerequisites")
        mocker.patch("subprocess.run")
        mocker.patch("yolo_cage.commands.build.sync_config_to_vm")
        mocker.patch("yolo_cage.commands.build.detect_local_repo", return_value=tmp_repo)

        # Provide a config file
        config_file = tmp_yolo_home / "test-config.env"
        config_file.write_text("GITHUB_PAT=test\nREPO_URL=https://github.com/test/repo\n")

        args = argparse.Namespace(
            instance="dev",
            config_file=str(config_file),
            interactive=False,
            up=False,
        )

        # Mock create_instance to set up the directory structure
        def mock_create_instance(name, repo_path=None):
            instances_dir = tmp_yolo_home / "instances" / name
            instances_dir.mkdir(parents=True, exist_ok=True)
            if repo_path:
                (instances_dir / "instance.json").write_text(f'{{"repo_path": "{repo_path}"}}')
            else:
                (instances_dir / "instance.json").write_text('{"repo_path": null}')
                (instances_dir / "repo").mkdir()
            return instances_dir

        with patch("yolo_cage.commands.build.create_instance", side_effect=mock_create_instance) as mock_create:
            cmd_build(args)

            # Check create_instance was called with repo_path
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            # Check repo_path was passed (either as kwarg or positional)
            assert call_args[1].get("repo_path") == tmp_repo or (len(call_args[0]) > 1 and call_args[0][1] == tmp_repo)
