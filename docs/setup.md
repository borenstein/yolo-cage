# Setup Guide

> **Note**: This setup provides defense-in-depth, not absolute security. Use scoped credentials and do not use production secrets. See [LICENSE](../LICENSE) for warranty disclaimers.

## Prerequisites

- **Kubernetes cluster**: Developed on MicroK8s; may require adaptation for other distributions
- **Container registry**: Accessible from your cluster (MicroK8s uses `localhost:32000`, or use Docker Hub, ECR, etc.)
- **Docker**: For building images locally
- **kubectl**: Configured to access your cluster
- **Claude account**: With OAuth credentials (Pro, Team, or Enterprise)

## Step 1: Clone the Repository

```bash
git clone https://github.com/borenstein/yolo-cage.git
cd yolo-cage
```

## Step 2: Build and Push Images

Build the three container images:

```bash
# Set your registry
REGISTRY=localhost:32000  # MicroK8s default

# Build sandbox image
docker build -t $REGISTRY/yolo-cage:latest -f dockerfiles/sandbox/Dockerfile .
docker push $REGISTRY/yolo-cage:latest

# Build dispatcher image
docker build -t $REGISTRY/git-dispatcher:latest -f dockerfiles/dispatcher/Dockerfile .
docker push $REGISTRY/git-dispatcher:latest

# Build proxy image
docker build -t $REGISTRY/egress-proxy:latest -f dockerfiles/proxy/Dockerfile .
docker push $REGISTRY/egress-proxy:latest
```

## Step 3: Create Namespace and Secrets

```bash
# Create namespace
kubectl create namespace yolo-cage
```

### GitHub PAT (Required)

Create a Personal Access Token for git operations:

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Create a token with `repo` scope (or use fine-grained tokens with specific permissions)

```bash
kubectl create secret generic github-pat \
  --namespace=yolo-cage \
  --from-literal=GITHUB_PAT=ghp_your_token_here
```

### Claude OAuth Credentials (Required)

Extract Claude credentials from an existing installation:

**On macOS:**
```bash
security find-generic-password -s "Claude Code" -w > claude-credentials.json
```

**On Linux:**
```bash
cp ~/.claude/.credentials.json claude-credentials.json
```

If you don't have credentials yet:
1. Install Claude Code: `npm install -g @anthropic-ai/claude-code`
2. Run `claude` and complete the OAuth flow
3. Extract credentials as above

Create the secret:
```bash
kubectl create secret generic yolo-cage-credentials \
  --namespace=yolo-cage \
  --from-file=claude-oauth-credentials=./claude-credentials.json

# Clean up
rm claude-credentials.json
```

## Step 4: Generate Proxy CA Certificate

The egress proxy needs a CA certificate for HTTPS interception:

```bash
# Generate CA key and certificate
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem \
  -subj "/CN=yolo-cage-proxy-ca"

# Create ConfigMap
kubectl create configmap proxy-ca \
  --namespace=yolo-cage \
  --from-file=mitmproxy-ca.pem=ca-cert.pem

# Clean up
rm ca-key.pem ca-cert.pem
```

## Step 5: Configure the Dispatcher

Edit the dispatcher config with your git identity:

```bash
# Edit the configmap
$EDITOR manifests/base/dispatcher/configmap.yaml
```

Update these values:
```yaml
data:
  GIT_USER_NAME: "Your Name"
  GIT_USER_EMAIL: "you@example.com"
```

## Step 6: Deploy

### Option A: Direct Apply (Quick Start)

```bash
kubectl apply -k manifests/base
```

### Option B: Kustomize Overlay (Recommended for Customization)

Create your overlay within the cloned repository:

```bash
# Copy the example overlay
cp -r manifests/overlays/example manifests/overlays/my-project

# Edit your overlay
$EDITOR manifests/overlays/my-project/kustomization.yaml

# Apply
kubectl apply -k manifests/overlays/my-project
```

Your overlay's `kustomization.yaml` should reference the base via relative path:

```yaml
resources:
  - ../../base
```

> **Note**: Kustomize remote bases (e.g., `https://github.com/.../base?ref=main`) do not work reliably across all Kubernetes distributions due to git integration issues. Always use a local clone with relative paths. See [issue #6](https://github.com/borenstein/yolo-cage/issues/6) for Helm-based installation (coming soon).

Wait for all pods to be ready:

```bash
kubectl get pods -n yolo-cage -w
```

Expected:
```
NAME                              READY   STATUS    RESTARTS   AGE
git-dispatcher-xxx                1/1     Running   0          1m
egress-proxy-xxx                  1/1     Running   0          1m
llm-guard-xxx                     1/1     Running   0          1m
```

## Step 7: Install the CLI

```bash
sudo cp scripts/yolo-cage /usr/local/bin/
sudo chmod +x /usr/local/bin/yolo-cage
```

## Step 8: Create Your First Sandbox

```bash
# Create a sandbox for a feature branch
yolo-cage create feature-auth

# Attach to the sandbox
yolo-cage attach feature-auth

# Inside the sandbox, start Claude Code
claude --dangerously-skip-permissions
```

## Verification

### Test proxying works:
```bash
kubectl exec -n yolo-cage deployment/git-dispatcher -- \
  curl -s https://api.github.com | head -5
```

Should return GitHub API response.

### Test secret scanning:
```bash
# From inside a sandbox pod
curl -X POST https://httpbin.org/post -d "secret=sk-ant-fake-key-12345"
```

Should return: `Blocked: request body contains potential secrets`

### Test git dispatcher:
```bash
# From inside a sandbox pod
git status
```

Should show repository status (or "yolo-cage:" message if not yet cloned).

## Troubleshooting

### Pod not starting

Check pod events:
```bash
kubectl describe pod -n yolo-cage <pod-name>
```

Common issues:
- Secret not created: Check `kubectl get secrets -n yolo-cage`
- PVC not bound: Check storage class exists
- Image pull error: Check registry access

### Git operations failing

Check dispatcher logs:
```bash
kubectl logs -n yolo-cage deployment/git-dispatcher
```

Common issues:
- "pod not registered": Wait for init script to complete, or pod IP changed
- Authentication errors: Check GitHub PAT secret

### Proxy blocking unexpectedly

Check proxy logs:
```bash
kubectl logs -n yolo-cage deployment/egress-proxy
```

All blocked requests are logged with reasons.

## Next Steps

- Read [Architecture](architecture.md) to understand the security model
- See [Customization](customization.md) for advanced configuration
