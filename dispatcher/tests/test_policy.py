"""Tests for branch enforcement policy."""

import pytest
from unittest.mock import patch

from dispatcher.policy import (
    get_checkout_target,
    check_branch_switch,
    check_merge_allowed,
    get_push_refspec_target,
    check_push_allowed,
    _has_url_target,
)


class TestGetCheckoutTarget:
    """Tests for extracting checkout/switch target branch."""

    def test_checkout_branch(self):
        assert get_checkout_target(["checkout", "feature"]) == "feature"

    def test_checkout_with_create_flag(self):
        assert get_checkout_target(["checkout", "-b", "new-branch"]) == "new-branch"

    def test_switch_branch(self):
        assert get_checkout_target(["switch", "main"]) == "main"

    def test_switch_with_create_flag(self):
        assert get_checkout_target(["switch", "-c", "new-branch"]) == "new-branch"

    def test_checkout_with_path_prefix(self):
        # Note: Current implementation doesn't handle -C /path prefix
        # This is a known limitation; the git shim doesn't use these flags.
        assert get_checkout_target(["-C", "/path", "checkout", "feature"]) is None

    def test_not_checkout_command(self):
        assert get_checkout_target(["branch", "feature"]) is None
        assert get_checkout_target(["status"]) is None

    def test_checkout_no_target(self):
        # Note: checkout - (previous branch) starts with -, so is treated as a flag
        # This is a known limitation.
        assert get_checkout_target(["checkout", "-"]) is None

    def test_checkout_with_double_dash(self):
        # git checkout -- file.txt (not a branch switch)
        result = get_checkout_target(["checkout", "--", "file.txt"])
        assert result == "file.txt"  # This is a limitation - we can't distinguish


class TestCheckBranchSwitch:
    """Tests for branch switch warnings."""

    def test_switch_to_assigned_branch_no_warning(self):
        result = check_branch_switch(["checkout", "feature"], "feature")
        assert result is None

    def test_switch_to_different_branch_warns(self):
        result = check_branch_switch(["checkout", "main"], "feature")
        assert result is not None
        assert "now viewing branch 'main'" in result
        assert "assigned branch is 'feature'" in result

    def test_switch_from_main_to_assigned_no_warning(self):
        result = check_branch_switch(["switch", "feature"], "feature")
        assert result is None

    def test_no_target_no_warning(self):
        result = check_branch_switch(["branch", "-a"], "feature")
        assert result is None


class TestCheckMergeAllowed:
    """Tests for merge/rebase/cherry-pick policy."""

    @patch("dispatcher.policy.get_current_branch")
    def test_merge_on_assigned_branch_allowed(self, mock_get_branch):
        mock_get_branch.return_value = "feature"
        result = check_merge_allowed("/workspace", "feature", "merge")
        assert result is None

    @patch("dispatcher.policy.get_current_branch")
    def test_merge_on_different_branch_denied(self, mock_get_branch):
        mock_get_branch.return_value = "main"
        result = check_merge_allowed("/workspace", "feature", "merge")
        assert result is not None
        assert "only merge while on your assigned branch" in result
        assert "'feature'" in result

    @patch("dispatcher.policy.get_current_branch")
    def test_rebase_on_different_branch_denied(self, mock_get_branch):
        mock_get_branch.return_value = "other"
        result = check_merge_allowed("/workspace", "feature", "rebase")
        assert result is not None
        assert "only rebase while on your assigned branch" in result

    @patch("dispatcher.policy.get_current_branch")
    def test_cherry_pick_on_assigned_allowed(self, mock_get_branch):
        mock_get_branch.return_value = "feature"
        result = check_merge_allowed("/workspace", "feature", "cherry-pick")
        assert result is None


class TestGetPushRefspecTarget:
    """Tests for extracting push refspec target."""

    def test_no_refspec(self):
        assert get_push_refspec_target(["push"]) is None
        assert get_push_refspec_target(["push", "origin"]) is None
        assert get_push_refspec_target(["push", "origin", "feature"]) is None

    def test_simple_refspec(self):
        assert get_push_refspec_target(["push", "origin", "local:remote"]) == "remote"

    def test_head_to_branch_refspec(self):
        assert get_push_refspec_target(["push", "origin", "HEAD:main"]) == "main"

    def test_empty_remote_ref(self):
        # git push origin :branch (delete remote branch)
        # Note: Current implementation returns 'branch', which would block this
        # as an attempt to push to a different branch. This is actually correct
        # behavior - we don't want agents deleting remote branches.
        assert get_push_refspec_target(["push", "origin", ":branch"]) == "branch"

    def test_refspec_with_flags(self):
        assert get_push_refspec_target(["push", "--force", "origin", "local:remote"]) == "remote"

    def test_flag_with_colon_not_refspec(self):
        # Flags containing colons should be ignored
        result = get_push_refspec_target(["push", "--receive-pack=git:receive-pack", "origin"])
        assert result is None  # Current implementation might not handle this perfectly


class TestCheckPushAllowed:
    """Tests for push policy enforcement."""

    @patch("dispatcher.policy.get_current_branch")
    def test_push_from_assigned_branch_allowed(self, mock_get_branch):
        mock_get_branch.return_value = "feature"
        result = check_push_allowed(["push", "origin", "feature"], "/workspace", "feature")
        assert result is None

    @patch("dispatcher.policy.get_current_branch")
    def test_push_from_wrong_branch_denied(self, mock_get_branch):
        mock_get_branch.return_value = "main"
        result = check_push_allowed(["push"], "/workspace", "feature")
        assert result is not None
        assert "can only push from your assigned branch" in result
        assert "'feature'" in result

    @patch("dispatcher.policy.get_current_branch")
    def test_push_to_different_remote_branch_denied(self, mock_get_branch):
        mock_get_branch.return_value = "feature"
        result = check_push_allowed(["push", "origin", "HEAD:main"], "/workspace", "feature")
        assert result is not None
        assert "can only push to branch 'feature'" in result

    @patch("dispatcher.policy.get_current_branch")
    def test_push_to_assigned_branch_via_refspec_allowed(self, mock_get_branch):
        mock_get_branch.return_value = "feature"
        result = check_push_allowed(["push", "origin", "HEAD:feature"], "/workspace", "feature")
        assert result is None

    @patch("dispatcher.policy.get_current_branch")
    def test_push_with_force_from_assigned_allowed(self, mock_get_branch):
        mock_get_branch.return_value = "feature"
        result = check_push_allowed(["push", "--force", "origin", "feature"], "/workspace", "feature")
        assert result is None

    @patch("dispatcher.policy.get_current_branch")
    def test_push_default_from_assigned_allowed(self, mock_get_branch):
        mock_get_branch.return_value = "feature"
        result = check_push_allowed(["push"], "/workspace", "feature")
        assert result is None


class TestHasUrlTarget:
    """Tests for URL detection in push commands."""

    def test_https_url(self):
        assert _has_url_target(["push", "https://github.com/owner/repo.git"]) is True

    def test_http_url(self):
        assert _has_url_target(["push", "http://github.com/owner/repo.git"]) is True

    def test_git_ssh_url(self):
        assert _has_url_target(["push", "git@github.com:owner/repo.git"]) is True

    def test_remote_name_only(self):
        assert _has_url_target(["push", "origin"]) is False

    def test_remote_with_branch(self):
        assert _has_url_target(["push", "origin", "feature"]) is False

    def test_remote_with_refspec(self):
        assert _has_url_target(["push", "origin", "HEAD:feature"]) is False

    def test_url_with_branch(self):
        assert _has_url_target(["push", "https://github.com/owner/repo.git", "feature"]) is True

    def test_flags_ignored(self):
        assert _has_url_target(["push", "--force", "origin"]) is False


class TestCrossRepoEscape:
    """Tests for cross-repository escape prevention."""

    @patch("dispatcher.policy.get_current_branch")
    def test_push_to_https_url_blocked(self, mock_get_branch):
        mock_get_branch.return_value = "feature"
        result = check_push_allowed(
            ["push", "https://github.com/other/repo.git", "feature"],
            "/workspace",
            "feature"
        )
        assert result is not None
        assert "URLs is not permitted" in result

    @patch("dispatcher.policy.get_current_branch")
    def test_push_to_git_ssh_url_blocked(self, mock_get_branch):
        mock_get_branch.return_value = "feature"
        result = check_push_allowed(
            ["push", "git@github.com:other/repo.git", "feature"],
            "/workspace",
            "feature"
        )
        assert result is not None
        assert "URLs is not permitted" in result

    @patch("dispatcher.policy.get_current_branch")
    def test_push_to_origin_allowed(self, mock_get_branch):
        mock_get_branch.return_value = "feature"
        result = check_push_allowed(["push", "origin", "feature"], "/workspace", "feature")
        assert result is None
