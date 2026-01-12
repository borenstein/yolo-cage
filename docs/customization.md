# Customization Guide

> **Note**: When customizing, maintain the security properties: non-root user, NetworkPolicy egress restrictions, and proxy-based scanning. Disabling these components removes the exfiltration controls.

## Changing the Development Environment

### Adding Languages/Tools

Edit `dockerfiles/sandbox/Dockerfile` to add your stack:

```dockerfile
# Example: Add Go
RUN curl -LO https://go.dev/dl/go1.22.0.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go1.22.0.linux-amd64.tar.gz \
    && rm go1.22.0.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:$PATH"

# Example: Add Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"
```

Rebuild and push:
```bash
docker build -t <registry>/yolo-cage:latest -f dockerfiles/sandbox/Dockerfile .
docker push <registry>/yolo-cage:latest
kubectl rollout restart -n <namespace> deployment/yolo-cage
```

### Resource Limits

Edit `manifests/sandbox/deployment.yaml`:

```yaml
resources:
  requests:
    cpu: "2"        # Minimum CPU
    memory: "8Gi"   # Minimum memory
  limits:
    cpu: "8"        # Maximum CPU
    memory: "32Gi"  # Maximum memory
```

Increase for large codebases or memory-intensive builds.

## Adding Secret Patterns

### Regex Patterns

Edit `manifests/proxy/llm-guard-config.yaml`:

```yaml
- type: Regex
  params:
    patterns:
      # Existing patterns...

      # Add your own:
      - "PRIVATE_KEY_[A-Za-z0-9]{32}"  # Your internal format
      - "mycompany_api_[a-f0-9]{40}"   # Company-specific tokens
    match_type: "search"
    redact: true
```

### Adding to Domain Blocklist

Edit `dockerfiles/proxy/secret_scanner.py`:

```python
BLOCKED_DOMAINS = {
    # Existing...

    # Add more:
    "webhook.site",
    "requestbin.com",
    "your-honeypot.example.com",
}
```

## Different Kubernetes Distributions

### MicroK8s

Default configuration. Uses:
- `localhost:32000` registry
- `microk8s kubectl` commands

### k3s

Change registry to your configured registry or use Docker Hub:
```yaml
# manifests/config.yaml
registry: docker.io/yourusername
```

### EKS/GKE/AKS

Use ECR/GCR/ACR respectively:
```yaml
registry: 123456789.dkr.ecr.us-west-2.amazonaws.com/yolo-cage
```

Ensure your nodes can pull from the registry (IAM roles, service accounts, etc.).

### Kind (local development)

Load images directly:
```bash
docker build -t yolo-cage:latest -f dockerfiles/sandbox/Dockerfile .
kind load docker-image yolo-cage:latest

docker build -t egress-proxy:latest -f dockerfiles/proxy/Dockerfile .
kind load docker-image egress-proxy:latest
```

Update manifests to use local images:
```yaml
image: yolo-cage:latest
imagePullPolicy: Never
```

## Storage Classes

Default uses `data-hostpath`. Change for your cluster:

```yaml
# manifests/sandbox/pvc.yaml
spec:
  storageClassName: standard        # GKE
  storageClassName: gp2             # EKS
  storageClassName: default         # Most clusters
  storageClassName: local-path      # k3s
```

## Multiple Projects

To run sandboxes for multiple projects, deploy to different namespaces:

```bash
# Project A
kubectl create namespace project-a
# Create secrets, deploy manifests with namespace: project-a

# Project B
kubectl create namespace project-b
# Create secrets, deploy manifests with namespace: project-b
```

Each namespace is isolated with its own:
- yolo-cage pod
- Egress proxy
- LLM-Guard instance
- Workspace PVC

## Fail-Closed Mode

By default, if LLM-Guard is unavailable, requests pass through (logged). To block instead:

Edit `dockerfiles/proxy/secret_scanner.py`:

```python
def _scan_for_secrets(self, text: str) -> tuple[bool, list[str]]:
    # ...

    if not self.llm_guard_available:
        self._check_llm_guard()
        if not self.llm_guard_available:
            # CHANGE: Block instead of allow
            logger.error("LLM-Guard unavailable, blocking request")
            return True, ["scanner_unavailable"]
```

## Git over HTTPS (Instead of SSH)

To route all git traffic through the proxy (for scanning):

1. Use HTTPS URL in your config:
```yaml
repo_url: https://github.com/you/your-project.git
```

2. Create a GitHub personal access token with repo access

3. Configure git credential helper in `scripts/init-workspace`:
```bash
git config --global credential.helper store
echo "https://your-username:ghp_token@github.com" > ~/.git-credentials
```

4. Remove SSH from NetworkPolicy egress rules

Now all git operations go through the proxy and get scanned.

## First-Turn Prompts

New threads can automatically run a "first turn" prompt that orients the agent before you start working. This is useful for:

- Ensuring agents review documentation (CLAUDE.md) before making changes
- Running setup scripts so the agent understands the bootstrapped environment
- Getting a summary of the project state and latest commit

### Setup

Create `scripts/thread.first-turn.txt` with your prompt:

```bash
cp scripts/thread.first-turn.txt.example scripts/thread.first-turn.txt
# Edit to customize
```

Example prompt:
```
Please review this project's documentation and codebase, especially CLAUDE.md.
Then run the setup script(s). Return with a brief summary of what this repo is,
how it works, and indicate the SHA of the latest commit.
```

When `thread new <name>` creates a new worktree, it will pass this prompt to Claude automatically.

### Skipping the First Turn

If you don't want a first-turn prompt, simply don't create the file. The script checks for its existence and runs without a prompt if absent.

## Restricting GitHub CLI Access

In YOLO mode, the agent has full access to any tools installed in the container, including the GitHub CLI (`gh`). You may want agents to access issues for context without being able to merge PRs, delete branches, or modify repository settings.

### Solution: Fine-Grained Personal Access Tokens

GitHub's [fine-grained personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token) (free for all users) can be scoped to specific repositories and permissions.

### Creating an Issues-Only Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens](https://github.com/settings/tokens?type=beta)

2. Click **Generate new token**

3. Configure the token:
   - **Token name**: `yolo-cage-issues` (or similar)
   - **Expiration**: Choose based on your security needs
   - **Repository access**: Select **Only select repositories** and choose your project repo
   - **Permissions**: Under "Repository permissions", set:
     - **Issues**: Read and write
     - Leave all other permissions as "No access"

4. Click **Generate token** and copy it

### Configuring the Container

The deployment is pre-configured to mount an optional `yolo-cage-github-token` secret. Just create the secret:

```bash
kubectl create secret generic yolo-cage-github-token \
  --namespace=<your-namespace> \
  --from-literal=token=github_pat_xxxxx
```

The `init-workspace` script automatically configures `gh` if the token is present.

### What This Prevents

With an issues-only token, even if the agent runs commands like:
- `gh pr merge` - Fails (no PR permissions)
- `gh repo delete` - Fails (no admin permissions)
- `gh release create` - Fails (no contents permissions)

The security boundary is enforced at GitHub's API level, not by restricting which commands the agent can run.

## Disabling Components

### Run without secret scanning (not recommended)

Remove proxy-related environment variables from yolo-cage deployment:
```yaml
env:
  # Remove HTTP_PROXY, HTTPS_PROXY, etc.
```

Update NetworkPolicy to allow direct internet access.

### Run without LLM-Guard (regex only)

Modify `secret_scanner.py` to skip the LLM-Guard call and rely only on regex patterns. Less thorough but no external dependency.

## Observability

### Persistent Logging

Add a sidecar to ship logs:

```yaml
containers:
  - name: egress-proxy
    # ... existing config

  - name: log-shipper
    image: fluent/fluent-bit:latest
    volumeMounts:
      - name: proxy-logs
        mountPath: /var/log/proxy
```

### Metrics

LLM-Guard exposes Prometheus metrics. Add a ServiceMonitor if you have Prometheus Operator:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: llm-guard
spec:
  selector:
    matchLabels:
      app: llm-guard
  endpoints:
    - port: http
      path: /metrics
```
