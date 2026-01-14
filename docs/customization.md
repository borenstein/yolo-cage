# Customization Guide

This guide covers advanced customizations beyond the standard [Configuration Reference](configuration.md). For most deployments, you only need to edit the manifest files directly.

> **Note**: When customizing, maintain the security properties: non-root user, NetworkPolicy egress restrictions, and proxy-based scanning. Disabling these removes exfiltration controls.

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
```

## Adding Secret Patterns

### LLM-Guard Regex Patterns

Edit `manifests/proxy/llm-guard-config.yaml` to add custom secret patterns:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: llm-guard-config
  namespace: yolo-cage
data:
  scanners.yml: |
    input_scanners:
      - type: Secrets
        params:
          redact_mode: "all"
      - type: Regex
        params:
          patterns:
            # Default patterns
            - "-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"
            - "AKIA[0-9A-Z]{16}"
            - "sk-ant-[a-zA-Z0-9-_]+"
            - "ghp_[a-zA-Z0-9]{36}"
            - "github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}"
            # Add your custom patterns here
            - "PRIVATE_KEY_[A-Za-z0-9]{32}"
            - "mycompany_api_[a-f0-9]{40}"
          match_type: "search"
          redact: true
    output_scanners: []
    settings:
      lazy_load: false
      low_cpu_mem_usage: true
```

## Different Kubernetes Distributions

### MicroK8s

Default configuration. Uses `localhost:32000` registry.

### k3s

Use your configured registry or Docker Hub. Edit the `image:` fields in:
- `manifests/dispatcher/deployment.yaml`
- `manifests/proxy/egress-proxy.yaml`
- `manifests/proxy/llm-guard.yaml`
- `manifests/sandbox/pod-template.yaml`

Example:
```yaml
spec:
  containers:
    - name: yolo-cage
      image: docker.io/yourusername/yolo-cage:latest
```

### EKS/GKE/AKS

Use ECR/GCR/ACR respectively. Update image references as above:

```yaml
image: 123456789.dkr.ecr.us-west-2.amazonaws.com/yolo-cage:latest
```

Ensure your nodes can pull from the registry (IAM roles, service accounts, etc.).

### Kind (local development)

Load images directly:
```bash
docker build -t yolo-cage:latest -f dockerfiles/sandbox/Dockerfile .
kind load docker-image yolo-cage:latest
```

Update deployments to use local images with `imagePullPolicy: Never`:
```yaml
spec:
  containers:
    - name: yolo-cage
      image: yolo-cage:latest
      imagePullPolicy: Never
```

## Multiple Projects

For multiple projects, clone the repository once per project:

```bash
# Project A
git clone https://github.com/borenstein/yolo-cage.git yolo-cage-project-a
cd yolo-cage-project-a
# Edit manifests/namespace.yaml to use namespace: project-a
# Edit other manifests to use project-a namespace
# Configure for project A's repo, deploy

# Project B
git clone https://github.com/borenstein/yolo-cage.git yolo-cage-project-b
cd yolo-cage-project-b
# Edit manifests/namespace.yaml to use namespace: project-b
# Configure for project B's repo, deploy
```

Each namespace is isolated with its own:
- Agent pods
- Egress proxy
- LLM-Guard instance
- Workspace PVC
- Git dispatcher

See [Using a Different Namespace](configuration.md#using-a-different-namespace) for the namespace change procedure.

## Restricting GitHub CLI Access

In YOLO mode, agents have full access to the GitHub CLI (`gh`). Use fine-grained tokens to limit what agents can do.

### Creating an Issues-Only Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens](https://github.com/settings/tokens?type=beta)

2. Click **Generate new token**

3. Configure:
   - **Repository access**: Select specific repositories
   - **Permissions**: Set only "Issues: Read and write"

4. Create the secret:
```bash
kubectl create secret generic yolo-cage-github-token \
  --namespace=<namespace> \
  --from-literal=token=github_pat_xxxxx
```

With an issues-only token, commands like `gh pr merge` or `gh repo delete` will fail at GitHub's API level.

## Observability

### Persistent Logging

To ship logs to an external system, add a sidecar container to `manifests/proxy/egress-proxy.yaml`:

```yaml
spec:
  template:
    spec:
      containers:
        - name: egress-proxy
          # ... existing container ...
        - name: log-shipper
          image: fluent/fluent-bit:latest
          volumeMounts:
            - name: proxy-logs
              mountPath: /var/log/proxy
```

### Prometheus Metrics

LLM-Guard exposes Prometheus metrics. If using Prometheus Operator, create a ServiceMonitor:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: llm-guard
  namespace: yolo-cage
spec:
  selector:
    matchLabels:
      app: llm-guard
  endpoints:
    - port: http
      path: /metrics
```

## Disabling Components

### Run without secret scanning (not recommended)

To disable secret scanning, remove the proxy environment variables from `manifests/sandbox/pod-template.yaml` and update `manifests/sandbox/networkpolicy.yaml` to allow direct internet access. This removes exfiltration protection.

### Run without LLM-Guard

To rely only on the domain blocklist without LLM-Guard, modify `dockerfiles/proxy/addon.py` to skip the LLM-Guard call. Less thorough but removes the external dependency.
