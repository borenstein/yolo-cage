# yolo-cage: AI coding agents that can't exfiltrate secrets or merge their own PRs

![yolo-cage banner](yolo-cage-banner.jpg)

> **Disclaimer**: This reduces risk but does not eliminate it. Do not use with production secrets or credentials where exfiltration would be catastrophic. See the [license](#license) section below.

A sandboxed environment for running [Claude Code](https://docs.anthropic.com/en/docs/claude-code) in YOLO mode (`--dangerously-skip-permissions`). Egress filtering blocks secret exfiltration. Git/GitHub controls enforce "agent proposes, human disposes":

1. **Cannot exfiltrate secrets** - egress proxy scans all HTTP/HTTPS
2. **Cannot modify code outside its branch** - git dispatcher enforces
3. **Cannot merge its own PRs** - agent proposes, human disposes

---

## Quick Start

### Prerequisites

- **Vagrant** with libvirt provider (Linux headless) or VirtualBox (macOS/Windows)
- **8GB RAM, 4 CPUs** available for the VM
- **GitHub PAT** with `repo` scope
- **Claude account** (Pro, Team, or Enterprise)

### Install

```bash
# Download latest release
curl -fsSL https://github.com/borenstein/yolo-cage/releases/latest/download/yolo-cage -o yolo-cage
chmod +x yolo-cage
sudo mv yolo-cage /usr/local/bin/
```

### Build the VM

```bash
# One-time setup (interactive prompts for GitHub PAT, repo URL, etc.)
yolo-cage build --interactive --up

# Or with a config file
yolo-cage build --config-file my-config.env --up
```

### Daily Use

```bash
yolo-cage create feature-branch   # Create a sandbox
yolo-cage attach feature-branch   # Attach (Claude starts in tmux)
yolo-cage list                    # List all sandboxes
yolo-cage delete feature-branch   # Delete when done
yolo-cage down                    # Stop the VM
yolo-cage up                      # Start the VM again
```

### Config Format

Create `~/.yolo-cage/config.env`:

```bash
GITHUB_PAT=ghp_your_token_here
REPO_URL=https://github.com/your-org/your-repo.git
GIT_NAME=yolo-cage
GIT_EMAIL=yolo-cage@localhost
# CLAUDE_OAUTH=your_oauth_token  # Optional: skip device login
# PROXY_BYPASS=example.com       # Optional: additional domains to bypass proxy
```

### Torture-Test It First

Need to convince yourself (or your security team) it actually works?

**[Security Audit Guide](docs/security-audit.md)** - Fork this repo, deploy yolo-cage against itself, run escape tests. Includes a prompt that asks an AI agent to try to break out of the cage defined by the repo it's reading.

---

## The Problem

You want multiple AI agents working on your codebase in parallel, each on different feature branches, without babysitting permission prompts. But YOLO mode feels irresponsible because agents have what [Simon Willison calls the "lethal trifecta"](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/):

1. **Internet access** (docs, APIs, package registries)
2. **Code execution** (the whole point)
3. **Secrets** (API keys, SSH keys, credentials)

Any two are fine. All three create exfiltration risk.

## The Solution

The agent is a **proposer**, not an executor. All the permission prompts that would normally interrupt autonomous development are **deferred** to a single review when the agent opens a PR.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ Vagrant VM (MicroK8s cluster)                                       │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ yolo-cage    │  │ yolo-cage    │  │ yolo-cage    │              │
│  │ (feature-a)  │  │ (feature-b)  │  │ (bugfix-c)   │              │
│  │              │  │              │  │              │              │
│  │ /usr/bin/git │  │ /usr/bin/git │  │ /usr/bin/git │              │
│  │ (shim)       │  │ (shim)       │  │ (shim)       │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│         └────────────────┬┴─────────────────┘                       │
│                          │                                          │
│                          ▼                                          │
│                 ┌─────────────────┐                                 │
│                 │  Git Dispatcher │                                 │
│                 │                 │                                 │
│                 │ • Command gate  │                                 │
│                 │ • Branch enforce│                                 │
│                 │ • Pre-push hooks│                                 │
│                 │ • Real git here │                                 │
│                 └────────┬────────┘                                 │
│                          │                                          │
│         ┌────────────────┴────────────────┐                         │
│         ▼                                 ▼                         │
│  ┌─────────────┐                 ┌─────────────────┐               │
│  │   GitHub    │                 │  Egress Proxy   │               │
│  │  (HTTPS)    │                 │  (mitmproxy)    │               │
│  └─────────────┘                 └─────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

**One pod per branch.** Each agent gets its own isolated pod with:
- **State isolation**: Agents cannot interfere with each other's work
- **Incorruptible identity**: Dispatcher identifies agents by pod IP
- **Clean failure modes**: If one agent goes haywire, others are unaffected

---

## What Gets Blocked

**Secrets:**
- Anthropic API keys (`sk-ant-*`)
- AWS credentials (`AKIA*`)
- GitHub tokens (`ghp_*`, `github_pat_*`)
- SSH private keys
- Generic secrets (via detect-secrets heuristics)

**Domains:**
- Paste sites (pastebin.com, hastebin.com, etc.)
- File sharing (file.io, transfer.sh, 0x0.st, etc.)

**GitHub API:**
- `PUT /repos/*/pulls/*/merge` - Cannot merge PRs
- `DELETE /repos/*` - Cannot delete anything
- Webhooks, branch protection modifications

**Git Operations:**
- Push to non-assigned branches
- Remote management, credential access, config changes

## Known Limitations

- **Pre-push hooks only**: TruffleHog runs before push, not on every commit
- **Prompt injection**: The egress filter mitigates many attacks, but sophisticated encoding could bypass scanning

---

## CLI Reference

### VM Lifecycle

| Command | Description |
|---------|-------------|
| `build [--config-file FILE \| --interactive] [--up]` | Clone repo, write config, build VM, apply config |
| `rebuild` | Destroy and rebuild VM (preserves config) |
| `up` | Start VM |
| `down` | Stop VM |
| `destroy` | Remove VM entirely |
| `status` | Show VM and pod status |

### Pod Operations

| Command | Description |
|---------|-------------|
| `create <branch>` | Create a sandbox pod for the branch |
| `attach <branch>` | Attach to sandbox (tmux session with Claude) |
| `list` | List all sandbox pods |
| `delete <branch> [--clean]` | Delete a sandbox pod |
| `logs <branch>` | Tail pod logs |

---

## Documentation

- [Architecture](docs/architecture.md) - Design rationale, threat model, limitations
- [Configuration](docs/configuration.md) - Egress policy, bypasses, hooks
- [Security Audit](docs/security-audit.md) - Escape testing for enterprise audits

---

## License

MIT. See [LICENSE](LICENSE) for full text.

**Important**: This software is provided "as is", without warranty of any kind. From the license:

> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

## Credits

Designed by David Bruce Borenstein; planned and implemented by Claude. The agent built its own containment infrastructure, which is either very aligned or very meta, depending on your perspective.
