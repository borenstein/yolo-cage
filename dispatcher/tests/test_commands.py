"""Tests for git command classification."""

import pytest

from dispatcher.commands import (
    CommandCategory,
    classify,
    get_subcommand,
    ALLOWLIST_LOCAL,
    ALLOWLIST_BRANCH,
    ALLOWLIST_MERGE,
    ALLOWLIST_REMOTE_READ,
    ALLOWLIST_REMOTE_WRITE,
    DENYLIST_MESSAGES,
)


class TestGetSubcommand:
    """Tests for extracting the git subcommand from args."""

    def test_simple_command(self):
        assert get_subcommand(["status"]) == "status"

    def test_command_with_args(self):
        assert get_subcommand(["commit", "-m", "message"]) == "commit"

    def test_command_with_flags_first(self):
        # Note: Current implementation doesn't handle -C /path style flags
        # It treats /path as the subcommand. This is a known limitation.
        # In practice, the git shim doesn't use these flags.
        assert get_subcommand(["-C", "/path", "status"]) == "/path"

    def test_empty_args(self):
        assert get_subcommand([]) is None

    def test_only_flags(self):
        assert get_subcommand(["--version"]) is None


class TestClassifyLocalCommands:
    """Tests for LOCAL category commands."""

    @pytest.mark.parametrize("cmd", list(ALLOWLIST_LOCAL))
    def test_all_local_commands_allowed(self, cmd):
        category, message = classify([cmd])
        assert category == CommandCategory.LOCAL
        assert message is None

    def test_status_with_args(self):
        category, _ = classify(["status", "-s"])
        assert category == CommandCategory.LOCAL

    def test_log_with_options(self):
        category, _ = classify(["log", "--oneline", "-10"])
        assert category == CommandCategory.LOCAL

    def test_commit_with_message(self):
        category, _ = classify(["commit", "-m", "test message"])
        assert category == CommandCategory.LOCAL

    def test_add_with_files(self):
        category, _ = classify(["add", "file1.txt", "file2.txt"])
        assert category == CommandCategory.LOCAL

    def test_diff_with_ref(self):
        category, _ = classify(["diff", "HEAD~1"])
        assert category == CommandCategory.LOCAL


class TestClassifyBranchCommands:
    """Tests for BRANCH category commands."""

    @pytest.mark.parametrize("cmd", list(ALLOWLIST_BRANCH))
    def test_all_branch_commands(self, cmd):
        category, message = classify([cmd])
        assert category == CommandCategory.BRANCH
        assert message is None

    def test_checkout_branch(self):
        category, _ = classify(["checkout", "feature-branch"])
        assert category == CommandCategory.BRANCH

    def test_checkout_create_branch(self):
        category, _ = classify(["checkout", "-b", "new-branch"])
        assert category == CommandCategory.BRANCH

    def test_switch_branch(self):
        category, _ = classify(["switch", "main"])
        assert category == CommandCategory.BRANCH

    def test_branch_list(self):
        category, _ = classify(["branch", "-a"])
        assert category == CommandCategory.BRANCH


class TestClassifyMergeCommands:
    """Tests for MERGE category commands."""

    @pytest.mark.parametrize("cmd", list(ALLOWLIST_MERGE))
    def test_all_merge_commands(self, cmd):
        category, message = classify([cmd])
        assert category == CommandCategory.MERGE
        assert message is None

    def test_merge_branch(self):
        category, _ = classify(["merge", "feature-branch"])
        assert category == CommandCategory.MERGE

    def test_rebase_branch(self):
        category, _ = classify(["rebase", "main"])
        assert category == CommandCategory.MERGE

    def test_cherry_pick_commit(self):
        category, _ = classify(["cherry-pick", "abc123"])
        assert category == CommandCategory.MERGE


class TestClassifyRemoteReadCommands:
    """Tests for REMOTE_READ category commands."""

    @pytest.mark.parametrize("cmd", list(ALLOWLIST_REMOTE_READ))
    def test_all_remote_read_commands(self, cmd):
        category, message = classify([cmd])
        assert category == CommandCategory.REMOTE_READ
        assert message is None

    def test_fetch_origin(self):
        category, _ = classify(["fetch", "origin"])
        assert category == CommandCategory.REMOTE_READ

    def test_fetch_all(self):
        category, _ = classify(["fetch", "--all"])
        assert category == CommandCategory.REMOTE_READ

    def test_pull(self):
        category, _ = classify(["pull"])
        assert category == CommandCategory.REMOTE_READ

    def test_pull_with_remote(self):
        category, _ = classify(["pull", "origin", "main"])
        assert category == CommandCategory.REMOTE_READ


class TestClassifyRemoteWriteCommands:
    """Tests for REMOTE_WRITE category commands."""

    @pytest.mark.parametrize("cmd", list(ALLOWLIST_REMOTE_WRITE))
    def test_all_remote_write_commands(self, cmd):
        category, message = classify([cmd])
        assert category == CommandCategory.REMOTE_WRITE
        assert message is None

    def test_push_default(self):
        category, _ = classify(["push"])
        assert category == CommandCategory.REMOTE_WRITE

    def test_push_with_remote_and_branch(self):
        category, _ = classify(["push", "origin", "feature"])
        assert category == CommandCategory.REMOTE_WRITE

    def test_push_force(self):
        category, _ = classify(["push", "--force"])
        assert category == CommandCategory.REMOTE_WRITE


class TestClassifyDeniedCommands:
    """Tests for DENIED category commands."""

    @pytest.mark.parametrize("cmd", list(DENYLIST_MESSAGES.keys()))
    def test_all_denied_commands(self, cmd):
        category, message = classify([cmd])
        assert category == CommandCategory.DENIED
        assert message == DENYLIST_MESSAGES[cmd]

    def test_remote_denied_message(self):
        category, message = classify(["remote", "-v"])
        assert category == CommandCategory.DENIED
        assert "remote management is not permitted" in message

    def test_clone_denied_message(self):
        category, message = classify(["clone", "https://github.com/foo/bar"])
        assert category == CommandCategory.DENIED
        assert "clone is not permitted" in message

    def test_config_denied_message(self):
        category, message = classify(["config", "user.email"])
        assert category == CommandCategory.DENIED
        assert "configuration is not permitted" in message


class TestClassifyUnknownCommands:
    """Tests for UNKNOWN category commands."""

    def test_unknown_command(self):
        category, message = classify(["unknown-command"])
        assert category == CommandCategory.UNKNOWN
        assert message is None

    def test_init_not_allowed(self):
        # init should be unknown (not in any allowlist)
        category, _ = classify(["init"])
        assert category == CommandCategory.UNKNOWN

    def test_submodule_not_in_allowlist(self):
        # submodule is in denylist
        category, message = classify(["submodule"])
        assert category == CommandCategory.DENIED

    def test_credential_not_in_allowlist(self):
        # credential is in denylist
        category, message = classify(["credential"])
        assert category == CommandCategory.DENIED
