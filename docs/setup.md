# Setup Guide

> **Note**: This setup provides defense-in-depth, not absolute security. Use scoped credentials and do not use production secrets. See [LICENSE](../LICENSE) for warranty disclaimers.

## Prerequisites

- **Vagrant**: With libvirt provider (Linux) or QEMU (macOS)
- **8GB RAM, 4 CPUs**: Available for the VM
- **GitHub PAT**: With `repo` scope ([create one here](https://github.com/settings/tokens))
- **Claude account**: Pro, Team, or Enterprise

### Installing Vagrant

**Ubuntu/Debian (libvirt):**
```bash
sudo apt install vagrant vagrant-libvirt qemu-kvm libvirt-daemon-system
sudo usermod -aG libvirt $USER
# Log out and back in
```

**Fedora (libvirt):**
```bash
sudo dnf install vagrant vagrant-libvirt
sudo usermod -aG libvirt $USER
# Log out and back in
```

**macOS (QEMU) - Experimental:**
```bash
brew install vagrant qemu
vagrant plugin install vagrant-qemu
```

> ⚠️ **Apple Silicon support is experimental.** The vagrant-qemu plugin has known
> limitations including unreliable port forwarding.

## Install

Download the latest release:

```bash
curl -fsSL https://github.com/borenstein/yolo-cage/releases/latest/download/yolo-cage -o yolo-cage
chmod +x yolo-cage
sudo mv yolo-cage /usr/local/bin/
```

### Install from Repository

To run from the repo (for testing PRs, development, or unreleased features):

```bash
git clone https://github.com/borenstein/yolo-cage.git
cd yolo-cage
./scripts/yolo-cage build --interactive --up
```

All commands work the same way - just use `./scripts/yolo-cage` instead of `yolo-cage`.

**Testing a PR:**

```bash
gh pr checkout 38
./scripts/yolo-cage build
```

## Quick Start

### Option A: Interactive Setup

```bash
yolo-cage build --interactive --up
```

You'll be prompted for:
- GitHub PAT
- Repository URL
- Git name and email (optional, defaults to "yolo-cage")
- Claude OAuth token (optional, use device login flow if skipped)
- Proxy bypass domains (optional)

### Option B: Config File Setup

Create a config file (e.g., `my-config.env`):

```bash
GITHUB_PAT=ghp_your_token_here
REPO_URL=https://github.com/your-org/your-repo.git
GIT_NAME=yolo-cage
GIT_EMAIL=yolo-cage@localhost
# CLAUDE_OAUTH=your_oauth_token
# PROXY_BYPASS=example.com,internal.corp
```

Then build:

```bash
yolo-cage build --config-file my-config.env --up
```

## What Happens During Build

1. Config is saved to `~/.yolo-cage/config.env`
2. Vagrant creates an Ubuntu VM with MicroK8s
3. Docker images are built inside the VM
4. Kubernetes manifests are applied
5. Config is synced to VM and applied to the cluster

The build takes 5-10 minutes on first run.

## Create Your First Sandbox

```bash
# Create a sandbox for a feature branch
yolo-cage create feature-auth

# Attach to the sandbox (launches Claude in tmux)
yolo-cage attach feature-auth
```

The session runs inside tmux:
- **Detach**: Press `Ctrl+B, D` to detach without ending the session
- **Reattach**: Run `yolo-cage attach feature-auth` to resume

## Daily Workflow

```bash
# Start the VM (if stopped)
yolo-cage up

# List existing sandboxes
yolo-cage list

# Create new sandbox or attach to existing
yolo-cage create my-branch
yolo-cage attach my-branch

# When done for the day
yolo-cage down
```

## Claude Authentication

On first attach to any sandbox, you'll complete the standard OAuth device flow:
1. Claude displays a URL and code
2. Open the URL in your browser
3. Enter the code to authorize

After that, all sandbox pods share the same credentials.

**Alternative**: Set `CLAUDE_OAUTH` in your config to skip the device flow.

## Troubleshooting

### VM won't start

Check Vagrant status:
```bash
cd ~/.yolo-cage/repo  # or your cloned repo
vagrant status
vagrant up --debug
```

### Pod not starting

Check pod events:
```bash
yolo-cage status
vagrant ssh -c "kubectl describe pod -n yolo-cage <pod-name>"
```

### Git operations failing

Check dispatcher logs:
```bash
vagrant ssh -c "kubectl logs -n yolo-cage deployment/git-dispatcher"
```

### Rebuild from scratch

If something goes wrong:
```bash
yolo-cage build
```

This destroys any existing VM and rebuilds it, preserving your config.

## Uninstall

### Remove everything

```bash
# Destroy the VM and all data
yolo-cage destroy

# Remove config and cloned repo
rm -rf ~/.yolo-cage

# Remove the CLI
sudo rm /usr/local/bin/yolo-cage
```

### Keep config, remove VM

```bash
# Destroy just the VM (keeps ~/.yolo-cage/config.env)
yolo-cage destroy
```

## Reinstall

### Fresh install (new config)

```bash
# Remove everything
yolo-cage destroy
rm -rf ~/.yolo-cage
sudo rm /usr/local/bin/yolo-cage

# Download latest release
curl -fsSL https://github.com/borenstein/yolo-cage/releases/latest/download/yolo-cage -o yolo-cage
chmod +x yolo-cage
sudo mv yolo-cage /usr/local/bin/

# Build with new config
yolo-cage build --interactive --up
```

### Upgrade to latest version

```bash
# Update CLI and repo (keeps VM running)
yolo-cage upgrade

# Update CLI, repo, and rebuild VM
yolo-cage upgrade --rebuild
```

## Next Steps

- Read [Architecture](architecture.md) to understand the security model
- See [Configuration](configuration.md) for all configuration options
- See [Security Audit](security-audit.md) to test the containment
