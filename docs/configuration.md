# Configuration Reference

This document covers all configuration options for yolo-cage. All configuration is done through Kubernetes manifests - you should never need to edit Python code or Dockerfiles.

## Quick Start

1. Copy the example overlay: `cp -r manifests/overlays/example manifests/overlays/myproject`
2. Edit `manifests/overlays/myproject/kustomization.yaml`
3. Apply: `kubectl apply -k manifests/overlays/myproject`

All configuration goes in your overlay's `kustomization.yaml`. The sections below explain each option.

---

## Namespace

```yaml
# Your project's namespace
namespace: my-project

# Also update the Namespace resource name to match
patches:
  - target:
      kind: Namespace
      name: yolo-cage
    patch: |
      - op: replace
        path: /metadata/name
        value: my-project
```

---

## Git Identity

The identity used for commits made by agents. **Required** - you must set this.

```yaml
configMapGenerator:
  - name: dispatcher-config
    behavior: replace
    literals:
      - GIT_USER_NAME=Your Name
      - GIT_USER_EMAIL=you@example.com
```

---

## Egress Policy

Controls what network traffic agents can make. All settings are in the `egress-policy` ConfigMap.

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
configMapGenerator:
  - name: egress-policy
    behavior: merge
    literals:
      # Comma-separated list of hosts
      - PROXY_BYPASS=api.anthropic.com,my-mcp-server.internal,vault.internal
```

Default: `api.anthropic.com`

### Blocked Domains

Domains the proxy will reject. Use for known exfiltration sites.

```yaml
configMapGenerator:
  - name: egress-policy
    behavior: merge
    literals:
      - |
        BLOCKED_DOMAINS=[
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
configMapGenerator:
  - name: egress-policy
    behavior: merge
    literals:
      - |
        GITHUB_API_BLOCKED=[
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

```yaml
configMapGenerator:
  - name: dispatcher-config
    behavior: replace
    literals:
      # JSON array of shell commands
      - PRE_PUSH_HOOKS=["trufflehog git file://. --max-depth=10 --fail --no-update"]
```

Default: TruffleHog secret scanning

### Examples

Run tests before push:
```yaml
- PRE_PUSH_HOOKS=["trufflehog git file://. --max-depth=10 --fail", "pytest tests/quick/"]
```

Lint check:
```yaml
- PRE_PUSH_HOOKS=["trufflehog git file://. --fail", "./scripts/lint.sh"]
```

Disable all hooks (not recommended):
```yaml
- PRE_PUSH_HOOKS=[]
```

---

## Commit Footer

Text appended to every commit message. Useful for tracking agent-generated commits.

```yaml
configMapGenerator:
  - name: dispatcher-config
    behavior: replace
    literals:
      - COMMIT_FOOTER=Built autonomously using yolo-cage v0.2.0
```

Set to empty string to disable:
```yaml
- COMMIT_FOOTER=
```

---

## Container Images

Override image locations for your registry.

```yaml
images:
  - name: localhost:32000/yolo-cage
    newName: your-registry.example.com/yolo-cage
    newTag: v0.2.0
  - name: localhost:32000/git-dispatcher
    newName: your-registry.example.com/git-dispatcher
    newTag: v0.2.0
  - name: localhost:32000/egress-proxy
    newName: your-registry.example.com/egress-proxy
    newTag: v0.2.0
```

---

## Storage

### Storage Class

The PVC uses your cluster's default storage class. To specify one:

```yaml
patches:
  - target:
      kind: PersistentVolumeClaim
      name: yolo-cage-workspaces
    patch: |
      - op: add
        path: /spec/storageClassName
        value: fast-ssd
```

### Storage Size

Default is 100Gi. To change:

```yaml
patches:
  - target:
      kind: PersistentVolumeClaim
      name: yolo-cage-workspaces
    patch: |
      - op: replace
        path: /spec/resources/requests/storage
        value: 500Gi
```

---

## Resource Limits

Adjust CPU and memory for components.

### Sandbox Pods

```yaml
patches:
  - target:
      kind: Deployment
      name: yolo-cage
    patch: |
      - op: replace
        path: /spec/template/spec/containers/0/resources/limits/memory
        value: 64Gi
      - op: replace
        path: /spec/template/spec/containers/0/resources/limits/cpu
        value: "16"
```

### Git Dispatcher

```yaml
patches:
  - target:
      kind: Deployment
      name: git-dispatcher
    patch: |
      - op: replace
        path: /spec/template/spec/containers/0/resources/limits/memory
        value: 8Gi
```

---

## Secrets

Create these secrets before deploying:

### Claude Credentials (Required)

```bash
kubectl create secret generic yolo-cage-credentials \
  --namespace=my-project \
  --from-file=claude-oauth-credentials=/path/to/credentials.json
```

### GitHub PAT (Required)

```bash
kubectl create secret generic github-pat \
  --namespace=my-project \
  --from-literal=GITHUB_PAT=ghp_your_token_here
```

The PAT needs these scopes:
- `repo` - Full repository access
- `read:org` - Read org membership (if using org repos)

---

## Complete Example

Here's a full `kustomization.yaml` for a production deployment:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: azimuth

patches:
  - target:
      kind: Namespace
      name: yolo-cage
    patch: |
      - op: replace
        path: /metadata/name
        value: azimuth
  - target:
      kind: PersistentVolumeClaim
      name: yolo-cage-workspaces
    patch: |
      - op: add
        path: /spec/storageClassName
        value: data-hostpath

configMapGenerator:
  - name: dispatcher-config
    behavior: replace
    literals:
      - GIT_USER_NAME=David Borenstein
      - GIT_USER_EMAIL=david@example.com
      - WORKSPACE_ROOT=/workspaces
      - YOLO_CAGE_VERSION=0.2.0
      - PRE_PUSH_HOOKS=["trufflehog git file://. --max-depth=10 --fail --no-update"]
      - COMMIT_FOOTER=Built autonomously using yolo-cage v0.2.0

  - name: egress-policy
    behavior: merge
    literals:
      - PROXY_BYPASS=api.anthropic.com,vault.internal

images:
  - name: localhost:32000/yolo-cage
    newName: localhost:32000/yolo-cage
    newTag: latest
  - name: localhost:32000/git-dispatcher
    newName: localhost:32000/git-dispatcher
    newTag: latest
  - name: localhost:32000/egress-proxy
    newName: localhost:32000/egress-proxy
    newTag: latest
```
