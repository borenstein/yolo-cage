# yolo-cage: AI coding agents that can't exfiltrate secrets or merge their own PRs

![yolo-cage banner](yolo-cage-banner.jpg)

> **Disclaimer**: This reduces risk but does not eliminate it. Do not use with production secrets or credentials where exfiltration would be catastrophic. See the [license](#license) section below.

A Kubernetes sandbox for running [Claude Code](https://docs.anthropic.com/en/docs/claude-code) in YOLO mode (`--dangerously-skip-permissions`). Egress filtering blocks secret exfiltration. Git/GitHub controls enforce "agent proposes, human disposes":

1. **Cannot exfiltrate secrets** - egress proxy scans all HTTP/HTTPS
2. **Cannot modify code outside its branch** - git dispatcher enforces
3. **Cannot merge its own PRs** - agent proposes, human disposes

---

## Get Started

### Option A: Deploy and Get to Work

Ready to go? → **[Setup Guide](docs/setup.md)**

### Option B: Torture-Test It First

Need to convince yourself (or your security team) it actually works?

→ **[Security Audit Guide](docs/security-audit.md)** - Fork this repo, deploy yolo-cage against itself, run escape tests. Includes a prompt that asks an AI agent to try to break out of the cage defined by the repo it's reading.

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
│ Kubernetes Cluster                                                   │
│                                                                      │
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
│  │  (HTTPS)    │                 │  (HTTP/HTTPS)   │               │
│  └─────────────┘                 └────────┬────────┘               │
│                                           │                         │
│                                           ▼                         │
│                                  ┌─────────────────┐               │
│                                  │   LLM-Guard     │               │
│                                  │ (secret scan)   │               │
│                                  └─────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

**One pod per branch.** Each agent gets its own isolated pod with:
- **State isolation**: Agents cannot interfere with each other's work
- **Incorruptible identity**: Dispatcher identifies agents by pod IP
- **Clean failure modes**: If one agent goes haywire, others are unaffected
- **Credential refresh**: When Claude re-authenticates, a sidecar propagates new credentials to k8s secrets so other pods pick them up on restart

### Git Shim Architecture

Claude Code uses git normally - all enforcement is transparent. A shim replaces `/usr/bin/git` and delegates to the dispatcher:

```
Agent runs: git commit -m "Add feature"
     │
     ▼
Shim intercepts, POSTs to dispatcher
     │
     ▼
Dispatcher enforces branch rules, runs TruffleHog, executes real git
     │
     ▼
Output returned to agent
```

## Documentation

- [Architecture](docs/architecture.md) - Design rationale, threat model, limitations
- [Setup](docs/setup.md) - Prerequisites, step-by-step deployment
- [Configuration](docs/configuration.md) - Egress policy, bypasses, hooks
- [Security Audit](docs/security-audit.md) - Escape testing for enterprise audits

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
- `GET /repos/*/actions/secrets/*` - Cannot read GH secrets
- Webhooks, branch protection modifications

**Git Operations:**
- Push to non-assigned branches
- Remote management, credential access, config changes

## Known Limitations

- **Pre-push hooks only**: TruffleHog runs before push, not on every commit
- **Prompt injection**: The egress filter mitigates many attacks, but sophisticated encoding could bypass scanning
- **Fail-closed**: If LLM-Guard is down, requests are blocked

## Requirements

- Kubernetes cluster (developed on MicroK8s)
- Container registry accessible from the cluster
- Docker (for building images)
- [Claude](https://claude.ai) account with OAuth credentials

## License

MIT. See [LICENSE](LICENSE) for full text.

**Important**: This software is provided "as is", without warranty of any kind. From the license:

> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

## Credits

Designed by David Bruce Borenstein; planned and implemented by Claude. The agent built its own containment infrastructure, which is either very aligned or very meta, depending on your perspective.
