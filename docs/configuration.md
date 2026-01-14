# Configuration Reference

This document covers all configuration options for yolo-cage. Configuration is done by editing YAML files directly in the `manifests/` directory.

## Configuration Files

| File | Purpose |
|------|---------|
| `manifests/dispatcher/configmap.yaml` | Repository URL, git identity, pre-push hooks, commit footer |
| `manifests/proxy/configmap.yaml` | Proxy bypass, blocked domains, GitHub API restrictions |
| `manifests/sandbox/configmap.yaml` | Custom init scripts, SSH known hosts |
| `manifests/sandbox/agent-prompt.yaml` | First-turn prompt, agent instructions |

---

## Repository URL

The repository URL to clone. **Required** - you must set this before deploying.

Edit `manifests/dispatcher/configmap.yaml`:

```yaml
data:
  REPO_URL: "https://github.com/your-org/your-project.git"
```

The dispatcher clones this repository when bootstrapping each workspace. Agents do not have clone access - they work with the pre-cloned workspace.

---

## Git Identity

The identity used for commits made by agents. **Required** - you must set this before deploying.

Edit `manifests/dispatcher/configmap.yaml`:

```yaml
data:
  GIT_USER_NAME: "Your Name"
  GIT_USER_EMAIL: "you@example.com"
```

---

## Egress Policy

Controls what network traffic agents can make. Edit `manifests/proxy/configmap.yaml`.

### Proxy Bypass

Hosts that bypass the scanning proxy entirely.

**Important:** Any service requiring authentication must be on the bypass list. The proxy scans all traffic for secrets - including legitimate API keys you *need* to send. If a service requires a token in a header or body, add it to PROXY_BYPASS or requests will be blocked.

Use for:
- **Authenticated APIs** (e.g., `api.anthropic.com`) - required, or your API key will be blocked
- **MCP servers** that require authentication
- **Internal services** with service tokens
- **Latency-sensitive services** where proxy overhead is unacceptable

Traffic to bypassed hosts is **not scanned for secrets** - this is why you should only bypass services you trust.

```yaml
data:
  # Comma-separated list of hosts or domain suffixes
  PROXY_BYPASS: ".anthropic.com,.claude.com,my-mcp-server.internal"
```

Use a leading dot (`.anthropic.com`) to match all subdomains. This is useful for services with multiple subdomains like Anthropic (api.anthropic.com, statsig.anthropic.com, etc.).

Default: `.anthropic.com,.claude.com`

### Blocked Domains

Domains the proxy will reject. Use for known exfiltration sites.

```yaml
data:
  BLOCKED_DOMAINS: |
    [
      "pastebin.com",
      "paste.ee",
      "hastebin.com",
      "your-blocked-site.com"
    ]
```

Default includes: pastebin.com, paste.ee, hastebin.com, dpaste.org, file.io, transfer.sh, 0x0.st, ix.io, sprunge.us, termbin.com

### GitHub API Restrictions

API endpoints the proxy will block. Defense-in-depth against agents performing dangerous operations.

```yaml
data:
  GITHUB_API_BLOCKED: |
    [
      ["PUT", "/repos/[^/]+/[^/]+/pulls/\\d+/merge"],
      ["DELETE", "/repos/.*"]
    ]
```

Default blocks:
- `PUT /repos/*/pulls/*/merge` - Cannot merge PRs
- `DELETE /repos/*`, `/orgs/*`, `/user/*` - Cannot delete anything
- `GET /repos/*/actions/secrets/*` - Cannot read GitHub secrets
- `PATCH /repos/*/*` - Cannot modify repo settings
- `PUT /repos/*/collaborators/*` - Cannot add collaborators
- `POST/PATCH /repos/*/hooks/*` - Cannot manage webhooks
- `PUT/DELETE /repos/*/branches/*/protection` - Cannot modify branch protection

---

## Pre-Push Hooks

Commands run before every `git push`. If any hook fails, the push is rejected.

Edit `manifests/dispatcher/configmap.yaml`:

```yaml
data:
  # JSON array of shell commands
  PRE_PUSH_HOOKS: '["trufflehog git file://. --max-depth=10 --fail --no-update"]'
```

Default: TruffleHog secret scanning

### Examples

Run tests before push:
```yaml
PRE_PUSH_HOOKS: '["trufflehog git file://. --max-depth=10 --fail", "pytest tests/quick/"]'
```

Lint check:
```yaml
PRE_PUSH_HOOKS: '["trufflehog git file://. --fail", "./scripts/lint.sh"]'
```

Disable all hooks (not recommended):
```yaml
PRE_PUSH_HOOKS: '[]'
```

---

## Commit Footer

Text appended to every commit message. Useful for tracking agent-generated commits.

Edit `manifests/dispatcher/configmap.yaml`:

```yaml
data:
  COMMIT_FOOTER: "Built autonomously using yolo-cage v0.2.0"
```

Set to empty string to disable:
```yaml
COMMIT_FOOTER: ""
```

---

## Custom Init Script

You can run a custom initialization script when each sandbox pod starts. This runs after the repository is cloned but before the agent begins working.

Edit `manifests/sandbox/configmap.yaml` to add an `init-workspace` key:

```yaml
data:
  init-workspace: |
    #!/bin/bash
    # Install project dependencies
    pip install -r requirements.txt
    npm install

    # Set up any project-specific configuration
    cp .env.example .env
```

The script:
- Runs with the same user as the agent (non-root)
- Has access to the cloned workspace at `/workspaces/{branch}`
- Can install packages, configure tools, etc.
- Fails the pod startup if it exits non-zero

Use this for project-specific setup that goes beyond what's in the base yolo-cage image.

---

## First-Turn Prompt

When you attach to a sandbox for the first time, Claude receives an initial prompt that orients it to the environment. Customize this for your project's workflow by editing [`manifests/sandbox/agent-prompt.yaml`](../manifests/sandbox/agent-prompt.yaml).

The prompt is only sent on the first attach to a new session. Subsequent attaches resume the existing conversation.

### Session Management

Sessions run inside tmux for persistence:

- **Detach**: Press `Ctrl+B, D` to detach without ending the session
- **Reattach**: Run `yolo-cage attach <branch>` to resume where you left off
- **Session state**: Conversation history, tool approvals, and working state are all preserved

This lets you disconnect (SSH timeout, switch tasks) and return later without losing context.

---

## Container Images

Images are specified in the deployment files. To use a different registry, edit:

- `manifests/dispatcher/deployment.yaml`
- `manifests/proxy/egress-proxy.yaml`
- `manifests/proxy/llm-guard.yaml`
- `manifests/sandbox/pod-template.yaml`

Find the `image:` field and update it:

```yaml
spec:
  containers:
    - name: yolo-cage
      image: your-registry.example.com/yolo-cage:v0.2.0
```

---

## Storage

### Storage Class

Edit `manifests/sandbox/pvc.yaml` to specify a storage class:

```yaml
spec:
  storageClassName: fast-ssd
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
```

### Storage Size

Edit `manifests/sandbox/pvc.yaml`:

```yaml
spec:
  resources:
    requests:
      storage: 500Gi
```

---

## Resource Limits

### Git Dispatcher

Edit `manifests/dispatcher/deployment.yaml`:

```yaml
spec:
  template:
    spec:
      containers:
        - name: git-dispatcher
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "1Gi"
              cpu: "1"
```

### Egress Proxy

Edit `manifests/proxy/egress-proxy.yaml`:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "1Gi"
    cpu: "1"
```

---

## Secrets

Create these secrets before deploying:

### Claude Credentials (Required)

```bash
kubectl create secret generic yolo-cage-credentials \
  --namespace=yolo-cage \
  --from-file=claude-oauth-credentials=/path/to/credentials.json
```

### GitHub PAT (Required)

```bash
kubectl create secret generic github-pat \
  --namespace=yolo-cage \
  --from-literal=GITHUB_PAT=ghp_your_token_here
```

The PAT needs these scopes:
- `repo` - Full repository access
- `read:org` - Read org membership (if using org repos)

---

## Using a Different Namespace

To deploy to a namespace other than `yolo-cage`:

1. Edit `manifests/namespace.yaml` to change the namespace name
2. Search and replace `yolo-cage` with your namespace in all manifest files:

```bash
find manifests -name "*.yaml" -exec sed -i 's/namespace: yolo-cage/namespace: my-project/g' {} \;
```

3. Create secrets in your namespace (Step 3 of setup)
4. Deploy as normal

---

## Configuration Files Reference

For complete examples, see the actual manifest files:

- [`manifests/dispatcher/configmap.yaml`](../manifests/dispatcher/configmap.yaml) - Repository URL, git identity, hooks
- [`manifests/proxy/configmap.yaml`](../manifests/proxy/configmap.yaml) - Proxy bypass, blocked domains
- [`manifests/sandbox/agent-prompt.yaml`](../manifests/sandbox/agent-prompt.yaml) - First-turn prompt
