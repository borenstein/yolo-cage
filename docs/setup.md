# Setup Guide

> **Note**: This setup provides defense-in-depth, not absolute security. Use scoped credentials and do not use production secrets. See [LICENSE](../LICENSE) for warranty disclaimers.

## Prerequisites

- **Vagrant**: With libvirt provider (Linux headless) or VirtualBox (macOS/Windows)
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

**macOS (VirtualBox):**
```bash
brew install vagrant
# Download VirtualBox from https://www.virtualbox.org/
```

## Quick Start

### Option A: Interactive Setup

```bash
git clone https://github.com/borenstein/yolo-cage.git
cd yolo-cage
./scripts/yolo-cage build --interactive --up
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
git clone https://github.com/borenstein/yolo-cage.git
cd yolo-cage
./scripts/yolo-cage build --config-file my-config.env --up
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
yolo-cage rebuild
```

This destroys the VM and rebuilds it, preserving your config.

## Next Steps

- Read [Architecture](architecture.md) to understand the security model
- See [Configuration](configuration.md) for all configuration options
- See [Security Audit](security-audit.md) to test the containment
