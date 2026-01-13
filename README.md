# yolo-cage: Safe, autonomous coding agents in Kubernetes

![yolo-cage banner](yolo-cage-banner.jpg)

> **Disclaimer**: This reduces risk but does not eliminate it. Do not use with production secrets or credentials where exfiltration would be catastrophic. See the [license](#license) section below.

A Kubernetes sandbox for running [Claude Code](https://docs.anthropic.com/en/docs/claude-code) agents in YOLO mode (`--dangerously-skip-permissions`) with robust containment:

1. **Cannot exfiltrate secrets** - egress proxy scans all HTTP/HTTPS
2. **Cannot modify code outside its branch** - git dispatcher enforces
3. **Cannot merge its own PRs** - agent proposes, human disposes

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

## Quick Start

```bash
# 1. Clone this repo
git clone https://github.com/borenstein/yolo-cage.git
cd yolo-cage

# 2. Create namespace and secrets
kubectl create namespace yolo-cage
kubectl create secret generic yolo-cage-credentials \
  --namespace=yolo-cage \
  --from-file=claude-oauth-credentials=claude-credentials.json

kubectl create secret generic github-pat \
  --namespace=yolo-cage \
  --from-literal=GITHUB_PAT=ghp_your_token_here

# 3. Build and push images (MicroK8s example)
docker build -t localhost:32000/yolo-cage:latest -f dockerfiles/sandbox/Dockerfile .
docker push localhost:32000/yolo-cage:latest

docker build -t localhost:32000/git-dispatcher:latest -f dockerfiles/dispatcher/Dockerfile .
docker push localhost:32000/git-dispatcher:latest

docker build -t localhost:32000/egress-proxy:latest -f dockerfiles/proxy/Dockerfile .
docker push localhost:32000/egress-proxy:latest

# 4. Deploy infrastructure
kubectl apply -n yolo-cage -f manifests/

# 5. Create a sandbox for your feature branch
./scripts/yolo-cage create feature-auth

# 6. Launch Claude
./scripts/yolo-cage attach feature-auth
```

## CLI Commands

```bash
yolo-cage create <branch> [-n namespace]   # Create pod for branch
yolo-cage list [-n namespace]              # List active pods
yolo-cage attach <branch> [-n namespace]   # Launch Claude in pod
yolo-cage delete <branch> [-n namespace]   # Remove pod
yolo-cage logs <branch> [-n namespace]     # Tail pod logs
```

## Documentation

- [Architecture](docs/architecture.md) - Why this approach, threat model, limitations
- [Setup](docs/setup.md) - Prerequisites, step-by-step deployment
- [Configuration](docs/configuration.md) - All configuration options (egress policy, bypasses, hooks, etc.)
- [Customization](docs/customization.md) - Advanced customizations (Dockerfile changes, different k8s distros)

---

## Choose Your Adventure

### Option A: Deploy and Get to Work

You've read enough. Deploy yolo-cage against your codebase and let agents start coding.

1. Follow the [Quick Start](#quick-start) above
2. Create a branch for each agent task
3. Let agents work autonomously
4. Review and merge their PRs

This is the happy path for teams that trust the architecture.

### Option B: Torture-Test It First

You need to convince yourself (or your security team) that this actually works before putting it anywhere near real code.

1. **Fork this repository** to a disposable copy
2. **Create a wide-open PAT** with all permissions (scoped to your fork only)
3. **Deploy yolo-cage against your fork** (the cage, caging itself)
4. **Run the escape tests**:
   - `yolo-cage-escape-test` - Automated deterministic testing
   - Agentic escape testing - An AI agent tries to break out

The [Security Audit Guide](docs/security-audit.md) walks you through this process step by step, including a specially crafted prompt that asks an AI agent to systematically attempt to escape its containment.

The prompt is meta by design: the agent reads the escape prompt from *this repository*, realizes it's being asked to test *its own cage*, and proceeds to try to break out. If it can't escape from a sandbox deployed against its own source code, you can be reasonably confident it won't escape from a sandbox deployed against yours.

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
