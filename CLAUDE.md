# yolo-cage

Run Claude Code in a sandboxed Kubernetes environment with git branch isolation.

## Quick Start

```bash
# One-time setup
yolo-cage build --interactive --up

# Daily use
yolo-cage create my-branch    # Create a sandbox
yolo-cage attach my-branch    # Connect to it
yolo-cage list                # List all sandboxes
yolo-cage delete my-branch    # Delete a sandbox
yolo-cage down                # Stop the VM
```

## Architecture

- **Host CLI** (`yolo-cage`): Runs on your machine, manages VM and delegates to inner CLI
- **Inner CLI** (`yolo-cage-inner`): Runs inside VM, manages pods
- **Vagrant VM**: Self-contained MicroK8s cluster
- **Dispatcher**: Manages git operations and pod lifecycle
- **Sandbox pods**: Isolated environments per branch
- **Egress proxy**: Filters outbound traffic

## Configuration

Create `~/.yolo-cage/config.env` with your credentials (or use `--interactive`):

```bash
GITHUB_PAT=ghp_your_token_here
REPO_URL=https://github.com/your-org/your-repo.git
GIT_NAME=yolo-cage
GIT_EMAIL=yolo-cage@localhost
# CLAUDE_OAUTH=your_oauth_token  # Optional
# PROXY_BYPASS=example.com       # Optional
```

## Development

### Prerequisites

- Vagrant with libvirt provider (for headless servers) or VirtualBox
- 8GB RAM, 4 CPUs available for the VM

### Testing changes

```bash
# Full rebuild from repo root
./scripts/yolo-cage rebuild

# Or manual testing
vagrant destroy -f && vagrant up
vagrant ssh
cp /home/vagrant/yolo-cage/config.env.example ~/.yolo-cage/config.env
# Edit config.env with your credentials
yolo-cage-configure
yolo-cage-inner create test-branch
yolo-cage-inner list
yolo-cage-inner delete test-branch
```

### CI Requirements

The main branch must always build successfully:
1. `vagrant up` completes without errors
2. `yolo-cage-configure` can apply a valid config
