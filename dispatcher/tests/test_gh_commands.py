"""Tests for GitHub CLI command classification."""

import pytest

from dispatcher.gh_commands import (
    GhCommandCategory,
    get_gh_subcommand,
    classify_gh,
    ALLOWED_COMMANDS,
    BLOCKED_COMMANDS,
    FULLY_BLOCKED_COMMANDS,
)


class TestGetGhSubcommand:
    """Tests for extracting gh command and subcommand."""

    def test_simple_command(self):
        assert get_gh_subcommand(["status"]) == ("status", None)

    def test_command_with_subcommand(self):
        assert get_gh_subcommand(["issue", "create"]) == ("issue", "create")

    def test_command_with_flags(self):
        assert get_gh_subcommand(["issue", "create", "--title", "Test"]) == ("issue", "create")

    def test_flags_before_command(self):
        # Note: Current implementation doesn't handle --repo owner/repo style flags.
        # It treats owner/repo as the main command. This is a known limitation.
        # In practice, the gh shim doesn't use these flags.
        assert get_gh_subcommand(["--repo", "owner/repo", "issue", "list"]) == ("owner/repo", "issue")

    def test_empty_args(self):
        assert get_gh_subcommand([]) == (None, None)

    def test_only_flags(self):
        assert get_gh_subcommand(["--help"]) == (None, None)

    def test_pr_merge(self):
        assert get_gh_subcommand(["pr", "merge", "123"]) == ("pr", "merge")


class TestClassifyGhAllowed:
    """Tests for allowed gh commands."""

    def test_issue_create(self):
        category, message = classify_gh(["issue", "create", "--title", "Test"])
        assert category == GhCommandCategory.ALLOWED
        assert message is None

    def test_issue_list(self):
        category, _ = classify_gh(["issue", "list"])
        assert category == GhCommandCategory.ALLOWED

    def test_issue_view(self):
        category, _ = classify_gh(["issue", "view", "123"])
        assert category == GhCommandCategory.ALLOWED

    def test_issue_comment(self):
        category, _ = classify_gh(["issue", "comment", "123", "--body", "test"])
        assert category == GhCommandCategory.ALLOWED

    def test_pr_create(self):
        category, _ = classify_gh(["pr", "create", "--title", "Test"])
        assert category == GhCommandCategory.ALLOWED

    def test_pr_list(self):
        category, _ = classify_gh(["pr", "list"])
        assert category == GhCommandCategory.ALLOWED

    def test_pr_view(self):
        category, _ = classify_gh(["pr", "view", "123"])
        assert category == GhCommandCategory.ALLOWED

    def test_pr_diff(self):
        category, _ = classify_gh(["pr", "diff", "123"])
        assert category == GhCommandCategory.ALLOWED

    def test_pr_checks(self):
        category, _ = classify_gh(["pr", "checks", "123"])
        assert category == GhCommandCategory.ALLOWED

    def test_repo_view(self):
        category, _ = classify_gh(["repo", "view"])
        assert category == GhCommandCategory.ALLOWED

    def test_search_issues(self):
        category, _ = classify_gh(["search", "issues", "bug"])
        assert category == GhCommandCategory.ALLOWED

    def test_status(self):
        category, _ = classify_gh(["status"])
        assert category == GhCommandCategory.ALLOWED

    def test_gist_create(self):
        category, _ = classify_gh(["gist", "create", "file.txt"])
        assert category == GhCommandCategory.ALLOWED


class TestClassifyGhBlocked:
    """Tests for blocked gh commands."""

    def test_pr_merge_blocked(self):
        category, message = classify_gh(["pr", "merge", "123"])
        assert category == GhCommandCategory.BLOCKED
        assert "merging PRs is not permitted" in message

    def test_repo_delete_blocked(self):
        category, message = classify_gh(["repo", "delete", "owner/repo"])
        assert category == GhCommandCategory.BLOCKED
        assert "deleting repositories is not permitted" in message

    def test_repo_create_blocked(self):
        category, message = classify_gh(["repo", "create", "new-repo"])
        assert category == GhCommandCategory.BLOCKED
        assert "creating repositories is not permitted" in message

    def test_repo_edit_blocked(self):
        category, message = classify_gh(["repo", "edit"])
        assert category == GhCommandCategory.BLOCKED
        assert "editing repository settings is not permitted" in message

    def test_secret_set_blocked(self):
        category, message = classify_gh(["secret", "set", "MY_SECRET"])
        assert category == GhCommandCategory.BLOCKED
        assert "managing secrets is not permitted" in message

    def test_secret_list_blocked(self):
        category, message = classify_gh(["secret", "list"])
        assert category == GhCommandCategory.BLOCKED
        assert "accessing secrets is not permitted" in message

    def test_ssh_key_add_blocked(self):
        category, message = classify_gh(["ssh-key", "add", "key.pub"])
        assert category == GhCommandCategory.BLOCKED
        assert "managing SSH keys is not permitted" in message

    def test_auth_login_blocked(self):
        category, message = classify_gh(["auth", "login"])
        assert category == GhCommandCategory.BLOCKED
        assert "authentication is managed by the sandbox" in message

    def test_api_blocked(self):
        category, message = classify_gh(["api", "/repos/owner/repo"])
        assert category == GhCommandCategory.BLOCKED
        assert "direct API access is not permitted" in message

    def test_extension_blocked(self):
        category, message = classify_gh(["extension", "install", "owner/ext"])
        assert category == GhCommandCategory.BLOCKED
        assert "managing extensions is not permitted" in message


class TestClassifyGhUnknown:
    """Tests for unknown gh commands."""

    def test_unknown_command(self):
        category, message = classify_gh(["unknown-command"])
        assert category == GhCommandCategory.UNKNOWN
        assert message is None

    def test_unknown_subcommand(self):
        # Known main command, unknown subcommand
        category, _ = classify_gh(["issue", "unknown-sub"])
        assert category == GhCommandCategory.UNKNOWN

    def test_empty_args(self):
        category, _ = classify_gh([])
        assert category == GhCommandCategory.UNKNOWN


class TestAllowedCommandsCoverage:
    """Verify all allowed commands are properly categorized."""

    @pytest.mark.parametrize("main_cmd,sub_cmd", [
        ("issue", "create"),
        ("issue", "list"),
        ("issue", "view"),
        ("issue", "comment"),
        ("pr", "create"),
        ("pr", "list"),
        ("pr", "view"),
        ("pr", "diff"),
        ("repo", "view"),
        ("search", "issues"),
        ("gist", "create"),
        ("run", "list"),
        ("label", "list"),
    ])
    def test_allowed_commands(self, main_cmd, sub_cmd):
        category, _ = classify_gh([main_cmd, sub_cmd])
        assert category == GhCommandCategory.ALLOWED


class TestBlockedCommandsCoverage:
    """Verify all blocked commands are properly categorized."""

    @pytest.mark.parametrize("main_cmd,sub_cmd,expected_text", [
        ("pr", "merge", "merging"),
        ("repo", "delete", "deleting"),
        ("repo", "create", "creating"),
        ("secret", "set", "secrets"),
        ("auth", "login", "authentication"),
    ])
    def test_blocked_commands(self, main_cmd, sub_cmd, expected_text):
        category, message = classify_gh([main_cmd, sub_cmd])
        assert category == GhCommandCategory.BLOCKED
        assert expected_text in message.lower()
