# Customization Guide

This guide covers advanced customizations that go beyond the standard [Configuration Reference](configuration.md). For most deployments, you only need to edit your kustomize overlay - see [Configuration Reference](configuration.md) first.

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

The LLM-Guard ConfigMap contains regex patterns for secret detection. To add patterns, patch the ConfigMap in your overlay:

```yaml
patches:
  - target:
      kind: ConfigMap
      name: llm-guard-config
    patch: |
      - op: add
        path: /data/scanners.yml
        value: |
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
                  # Your custom patterns
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

Use your configured registry or Docker Hub. Update images in your overlay:
```yaml
images:
  - name: localhost:32000/yolo-cage
    newName: docker.io/yourusername/yolo-cage
```

### EKS/GKE/AKS

Use ECR/GCR/ACR respectively:
```yaml
images:
  - name: localhost:32000/yolo-cage
    newName: 123456789.dkr.ecr.us-west-2.amazonaws.com/yolo-cage
```

Ensure your nodes can pull from the registry (IAM roles, service accounts, etc.).

### Kind (local development)

Load images directly:
```bash
docker build -t yolo-cage:latest -f dockerfiles/sandbox/Dockerfile .
kind load docker-image yolo-cage:latest
```

Update overlay to use local images:
```yaml
images:
  - name: localhost:32000/yolo-cage
    newName: yolo-cage
    newTag: latest
patches:
  - target:
      kind: Deployment
      name: yolo-cage
    patch: |
      - op: replace
        path: /spec/template/spec/containers/0/imagePullPolicy
        value: Never
```

## Multiple Projects

Deploy to different namespaces for multiple projects:

```bash
# Project A
kubectl apply -k manifests/overlays/project-a

# Project B
kubectl apply -k manifests/overlays/project-b
```

Each namespace is isolated with its own:
- Agent pods
- Egress proxy
- LLM-Guard instance
- Workspace PVC
- Git dispatcher

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

Add a sidecar to ship logs:

```yaml
patches:
  - target:
      kind: Deployment
      name: egress-proxy
    patch: |
      - op: add
        path: /spec/template/spec/containers/-
        value:
          name: log-shipper
          image: fluent/fluent-bit:latest
          volumeMounts:
            - name: proxy-logs
              mountPath: /var/log/proxy
```

### Prometheus Metrics

LLM-Guard exposes Prometheus metrics. Add a ServiceMonitor if using Prometheus Operator:

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

## Disabling Components

### Run without secret scanning (not recommended)

Remove proxy environment variables from your overlay and update NetworkPolicy to allow direct internet access. This removes exfiltration protection.

### Run without LLM-Guard

Modify `dockerfiles/proxy/addon.py` to skip the LLM-Guard call and rely only on domain blocklist. Less thorough but no external dependency.
