# Setup Guide

> **Note**: This setup provides defense-in-depth, not absolute security. Use scoped credentials (deploy keys, limited API tokens) and do not use production secrets. See [LICENSE](../LICENSE) for warranty disclaimers.

## Prerequisites

- **Kubernetes cluster**: Developed on MicroK8s; may require adaptation for other distributions
- **Container registry**: Accessible from your cluster (MicroK8s has `localhost:32000`, or use Docker Hub, ECR, etc.)
- **Docker**: For building images locally
- **kubectl**: Configured to access your cluster
- **Claude account**: With OAuth credentials (Pro, Team, or Enterprise)

## Step 1: Clone and Configure

```bash
git clone https://github.com/borenstein/yolo-cage.git
cd yolo-cage

# Copy the example config
cp manifests/config.example.yaml manifests/config.yaml
```

Edit `manifests/config.yaml`:

```yaml
namespace: dev-sandbox          # Your namespace name
registry: localhost:32000       # Your container registry
repo_url: git@github.com:you/your-project.git
git_name: Your Name
git_email: you@example.com
```

## Step 2: Create GitHub Deploy Key

Generate an SSH key pair for git access:

```bash
ssh-keygen -t ed25519 -C "yolo-cage-deploy" -f ./deploy-key -N ""
```

Add `deploy-key.pub` to your GitHub repo:
1. Go to your repo → Settings → Deploy keys
2. Add deploy key, paste the public key contents
3. Enable "Allow write access" if you want Claude to push

Keep `deploy-key` (private) for the next step.

## Step 3: Get Claude OAuth Credentials

Claude Code uses OAuth for authentication. You need to extract the credentials from a working installation.

### On macOS:

```bash
# Find the credential in Keychain
security find-generic-password -s "Claude Code" -w 2>/dev/null
```

If that returns JSON, save it:
```bash
security find-generic-password -s "Claude Code" -w > claude-credentials.json
```

### On Linux:

Check `~/.claude/.credentials.json` if you've previously authenticated.

### If you don't have credentials yet:

1. Install Claude Code locally: `npm install -g @anthropic-ai/claude-code`
2. Run `claude` and complete the OAuth flow in your browser
3. Extract credentials as above

## Step 4: Create Kubernetes Secrets

```bash
# Create namespace first
kubectl apply -f manifests/namespace.yaml

# Create the secrets
kubectl create secret generic yolo-cage-credentials \
  --namespace=<your-namespace> \
  --from-file=ssh-private-key=./deploy-key \
  --from-file=claude-oauth-credentials=./claude-credentials.json

# Clean up local copies
rm deploy-key deploy-key.pub claude-credentials.json
```

## Step 4b: Create GitHub Token (Optional)

If you want the agent to interact with GitHub Issues via the `gh` CLI, create a fine-grained personal access token:

1. Go to [GitHub Settings > Developer settings > Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. Click **Generate new token**
3. Configure:
   - **Token name**: `yolo-cage` (or similar)
   - **Repository access**: Select your project repo only
   - **Permissions**: Issues: Read and write (leave others as "No access")
4. Copy the token

Create the secret:

```bash
kubectl create secret generic yolo-cage-github-token \
  --namespace=<your-namespace> \
  --from-literal=token=github_pat_xxxxx
```

See [docs/customization.md](customization.md#restricting-github-cli-access) for details on what this prevents.

## Step 5: Build Container Images

### yolo-cage (Claude Code environment):

```bash
docker build -t <registry>/yolo-cage:latest -f dockerfiles/sandbox/Dockerfile .
docker push <registry>/yolo-cage:latest
```

For MicroK8s:
```bash
docker build -t localhost:32000/yolo-cage:latest -f dockerfiles/sandbox/Dockerfile .
docker push localhost:32000/yolo-cage:latest
```

### Egress Proxy:

```bash
docker build -t <registry>/egress-proxy:latest -f dockerfiles/proxy/Dockerfile .
docker push <registry>/egress-proxy:latest
```

## Step 6: Deploy

```bash
# Apply all manifests
kubectl apply -f manifests/namespace.yaml
kubectl apply -f manifests/proxy/
kubectl apply -f manifests/sandbox/

# Wait for LLM-Guard (downloads models on first start)
kubectl rollout status -n <namespace> deployment/llm-guard --timeout=300s

# Wait for other components
kubectl rollout status -n <namespace> deployment/egress-proxy --timeout=60s
kubectl rollout status -n <namespace> deployment/yolo-cage --timeout=60s
```

Or use the convenience script:
```bash
./deploy.sh
```

## Step 7: Initialize and Start Working

```bash
# Get into the pod
kubectl exec -it -n <namespace> deployment/yolo-cage -- bash

# First time: initialize workspace
init-workspace

# Start a new feature
thread new my-feature
```

This creates a git worktree at `/workspace/my-feature` and launches Claude Code in YOLO mode inside a tmux session.

## Verification

### Test that proxying works:

```bash
kubectl exec -n <namespace> deployment/yolo-cage -- \
  curl -s https://httpbin.org/get | head -5
```

Should return JSON from httpbin.

### Test that secret scanning works:

```bash
kubectl exec -n <namespace> deployment/yolo-cage -- \
  curl -s -X POST https://httpbin.org/post \
  -d "secret=sk-ant-fake-key-12345"
```

Should return: `Blocked: request body contains potential secrets`

### Test domain blocking:

```bash
kubectl exec -n <namespace> deployment/yolo-cage -- \
  curl -s https://pastebin.com
```

Should return: `Blocked: destination is on blocklist`

## Troubleshooting

### Pod won't start

Check events:
```bash
kubectl describe pod -n <namespace> -l app=yolo-cage
```

Things to check:
- Secret not created (check `kubectl get secrets -n <namespace>`)
- PVC not bound (check storage class exists)
- Image pull error (check registry access)

### HTTPS requests fail with SSL error

The proxy CA certificate might not be configured correctly. Check:
```bash
kubectl exec -n <namespace> deployment/yolo-cage -- \
  ls -la /etc/ssl/certs/ca-certificates-combined.crt
```

Should show a ~200KB file. If missing, check the init container logs:
```bash
kubectl logs -n <namespace> deployment/yolo-cage -c setup-ca
```

### LLM-Guard returns 500 errors

Check LLM-Guard logs:
```bash
kubectl logs -n <namespace> -l app=llm-guard
```

Things to check:
- Config syntax error (check `scanners.yml` format)
- Out of memory (increase limits)

### Requests pass through without scanning

Check if LLM-Guard is healthy:
```bash
kubectl exec -n <namespace> deployment/yolo-cage -- \
  curl -s http://llm-guard:8000/healthz
```

Should return `{"status":"healthy"}`.
