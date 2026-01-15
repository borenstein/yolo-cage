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

### Claude Authentication

Claude credentials are shared automatically across all sandbox pods via a persistent volume. No secret creation needed.

The first time you run `claude` in any sandbox pod, you'll complete the standard OAuth flow. After that, all sandbox pods share the same credentials—just like running multiple `claude` processes on a single laptop.

## Step 4: Generate Proxy CA Certificate

The egress proxy needs a CA certificate for HTTPS interception.

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

## Step 5: Configure

Edit the manifest files to set your configuration:

### Repository URL (Required)

Edit `manifests/dispatcher/configmap.yaml`:

```yaml
data:
  REPO_URL: "https://github.com/your-org/your-project.git"
```

### Git Identity (Required)

Also in `manifests/dispatcher/configmap.yaml`:

```yaml
data:
  GIT_USER_NAME: "Your Name"
  GIT_USER_EMAIL: "you@example.com"
```

### Proxy Bypass (Optional)

If you use MCP servers or other authenticated services, add them to `manifests/proxy/configmap.yaml`:

```yaml
data:
  PROXY_BYPASS: ".anthropic.com,.claude.com,my-mcp-server.internal"
```

The default (`.anthropic.com,.claude.com`) covers all Anthropic API endpoints. Use leading dots to match subdomains.

See [Configuration Reference](configuration.md) for all options.

## Step 6: Deploy

### Option A: Deploy Script (Recommended)

```bash
./deploy.sh
```

The script applies all manifests and waits for pods to be ready.

### Option B: Manual Apply

```bash
kubectl apply -f manifests/namespace.yaml
kubectl apply -f manifests/dispatcher/
kubectl apply -f manifests/proxy/configmap.yaml
kubectl apply -f manifests/proxy/egress-proxy.yaml
kubectl apply -f manifests/proxy/llm-guard.yaml
kubectl apply -f manifests/sandbox/
```

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

The CLI needs access to manifest templates. Choose one option:

### Option A: System Install (Recommended)

```bash
# Install CLI
sudo cp scripts/yolo-cage /usr/local/bin/
sudo chmod +x /usr/local/bin/yolo-cage

# Install manifests
sudo mkdir -p /usr/local/share/yolo-cage
sudo cp -r manifests /usr/local/share/yolo-cage/
```

### Option B: Environment Variable

If you prefer to keep everything in your cloned repo:

```bash
# Add to ~/.bashrc or ~/.zshrc
export YOLO_CAGE_HOME="$HOME/yolo-cage"
export PATH="$YOLO_CAGE_HOME/scripts:$PATH"
```

### Option C: Run from Repo

Simply run the CLI from your cloned directory:

```bash
~/yolo-cage/scripts/yolo-cage create feature-auth
```

## Step 8: Create Your First Sandbox

```bash
# Create a sandbox for a feature branch
yolo-cage create feature-auth

# Attach to the sandbox (launches Claude automatically)
yolo-cage attach feature-auth
```

On first attach, Claude receives a first-turn prompt and begins orienting to the project. The session runs inside tmux:

- **Detach**: Press `Ctrl+B, D` to detach without ending the session
- **Reattach**: Run `yolo-cage attach feature-auth` to resume
- **Customize**: Edit `manifests/sandbox/agent-prompt.yaml` to change the first-turn prompt

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
- See [Configuration](configuration.md) for all configuration options
- See [Customization](customization.md) for advanced customization
