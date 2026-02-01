# Integration Testing Guide

This document describes how to verify yolo-cage functionality works correctly. These tests are run by **developers** (or agents building yolo-cage) from **outside** the sandbox, not by sandboxed agents.

> **Note**: For security testing run by sandboxed agents, see [escape-testing.md](./escape-testing.md).

## Prerequisites

- A running yolo-cage instance with VM up
- The `yolo-cage` CLI available
- GitHub repository configured with appropriate PAT

## Test Categories

### 1. Sandbox Lifecycle

Verify sandboxes can be created, listed, and deleted.

```bash
# Create a sandbox for a new branch
yolo-cage create test-integration-$(date +%s)

# List sandboxes - should show the new one
yolo-cage list

# Delete the sandbox
yolo-cage delete <branch-name>
```

### 2. Git Operations

Verify the git-shim correctly proxies operations through the dispatcher.

```bash
# Attach to a sandbox
yolo-cage attach <branch-name>

# Inside the sandbox:
git status                    # Should work
git add .                     # Should work
git commit -m "test"          # Should work
git push origin <branch>      # Should work (to assigned branch only)
git push origin HEAD:main     # Should be BLOCKED
```

### 3. GitHub CLI Operations

Verify the gh-shim correctly proxies operations and transmits file content.

```bash
# Inside a sandbox:

# Test basic operations
gh issue list                 # Should work
gh pr list                    # Should work

# Test --body flag (should work)
gh issue create --title "Test" --body "Body content"

# Test --body-file with a file (verifies file content transmission)
echo "Issue body from file" > /tmp/body.md
gh issue create --title "Test body-file" --body-file /tmp/body.md

# Test --body-file with stdin (verifies stdin transmission)
echo "PR body from stdin" | gh pr create --title "Test stdin" --body-file -

# Blocked operations
gh pr merge 123               # Should be BLOCKED
gh repo delete owner/repo     # Should be BLOCKED
gh api /repos/owner/repo      # Should be BLOCKED
```

### 4. Network Egress

Verify the egress proxy allows legitimate traffic and blocks secrets.

```bash
# Inside a sandbox:

# Allowed: normal HTTP requests
curl https://httpbin.org/get

# Blocked: requests containing secrets
curl -X POST https://httpbin.org/post -d "token=ghp_abcdefghijklmnopqrstuvwxyz1234567890"
```

## Automated Integration Test Script

For CI or thorough verification, use the integration test script:

```bash
# From the host (outside sandbox), with instance running:
./scripts/integration-test.sh
```

This script:
1. Creates a test sandbox
2. Runs all verification commands
3. Cleans up the sandbox
4. Reports pass/fail status

## Troubleshooting

### Sandbox won't start
- Check `yolo-cage status` for VM state
- Check dispatcher logs: `yolo-cage logs dispatcher`

### Git operations fail
- Verify pod is registered: `curl http://localhost:8080/registry` (via port-forward)
- Check dispatcher logs for policy violations

### gh operations fail
- Verify GITHUB_PAT is configured
- Check if command is in the allowed list (see `dispatcher/gh_commands.py`)

## Adding New Integration Tests

When adding new features that affect sandbox behavior:

1. Add manual test commands to the relevant section above
2. Add automated checks to `scripts/integration-test.sh`
3. Document expected behavior (both success and failure cases)
