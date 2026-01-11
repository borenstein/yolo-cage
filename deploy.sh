#!/bin/bash
# Deploy yolo-cage to your Kubernetes cluster
#
# Prerequisites:
# 1. kubectl configured for your cluster
# 2. Docker installed for building images
# 3. manifests/config.yaml configured
# 4. yolo-cage-credentials secret created (see docs/setup.md)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Yolo-Cage Deployment ===${NC}"

# Check for config
if [[ ! -f manifests/config.yaml ]]; then
    echo -e "${RED}Error: manifests/config.yaml not found${NC}"
    echo "Copy manifests/config.example.yaml to manifests/config.yaml and edit it."
    exit 1
fi

# Parse config (basic YAML parsing)
NAMESPACE=$(grep "^namespace:" manifests/config.yaml | awk '{print $2}')
REGISTRY=$(grep "^registry:" manifests/config.yaml | awk '{print $2}')

if [[ -z "$NAMESPACE" || -z "$REGISTRY" ]]; then
    echo -e "${RED}Error: Could not parse namespace or registry from config.yaml${NC}"
    exit 1
fi

echo "Namespace: $NAMESPACE"
echo "Registry: $REGISTRY"
echo ""

# Build images
echo -e "${YELLOW}Building yolo-cage image...${NC}"
docker build -t "$REGISTRY/yolo-cage:latest" -f dockerfiles/sandbox/Dockerfile .

echo -e "${YELLOW}Building egress-proxy image...${NC}"
docker build -t "$REGISTRY/egress-proxy:latest" -f dockerfiles/proxy/Dockerfile .

# Push images
echo -e "${YELLOW}Pushing images to registry...${NC}"
docker push "$REGISTRY/yolo-cage:latest"
docker push "$REGISTRY/egress-proxy:latest"

# Apply manifests
echo -e "${YELLOW}Applying Kubernetes manifests...${NC}"

# Namespace first
kubectl apply -f manifests/namespace.yaml

# Check if secret exists
if ! kubectl get secret yolo-cage-credentials -n "$NAMESPACE" &>/dev/null; then
    echo -e "${RED}Error: Secret 'yolo-cage-credentials' not found in namespace '$NAMESPACE'${NC}"
    echo "Create it with:"
    echo "  kubectl create secret generic yolo-cage-credentials \\"
    echo "    --namespace=$NAMESPACE \\"
    echo "    --from-file=ssh-private-key=./deploy-key \\"
    echo "    --from-file=claude-oauth-credentials=./claude-credentials.json"
    exit 1
fi

# Proxy components
kubectl apply -f manifests/proxy/

# Wait for LLM-Guard
echo -e "${YELLOW}Waiting for LLM-Guard (this may take a while on first deploy)...${NC}"
kubectl rollout status -n "$NAMESPACE" deployment/llm-guard --timeout=300s || {
    echo -e "${YELLOW}Warning: LLM-Guard may still be starting up${NC}"
}

# Extract and apply proxy CA
echo -e "${YELLOW}Extracting proxy CA certificate...${NC}"
sleep 5  # Give proxy a moment to start
kubectl exec -n "$NAMESPACE" deployment/egress-proxy -- \
    cat /home/mitmproxy/.mitmproxy/mitmproxy-ca-cert.pem > /tmp/mitmproxy-ca.pem 2>/dev/null || {
    echo -e "${YELLOW}Warning: Could not extract CA cert. You may need to do this manually.${NC}"
}

if [[ -f /tmp/mitmproxy-ca.pem && -s /tmp/mitmproxy-ca.pem ]]; then
    kubectl create configmap proxy-ca \
        --namespace="$NAMESPACE" \
        --from-file=mitmproxy-ca.pem=/tmp/mitmproxy-ca.pem \
        --dry-run=client -o yaml | kubectl apply -f -
    rm /tmp/mitmproxy-ca.pem
fi

# Sandbox components
kubectl apply -f manifests/sandbox/

# Wait for yolo-cage
echo -e "${YELLOW}Waiting for yolo-cage...${NC}"
kubectl rollout status -n "$NAMESPACE" deployment/yolo-cage --timeout=120s

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "To get into the pod:"
echo "  kubectl exec -it -n $NAMESPACE deployment/yolo-cage -- bash"
echo ""
echo "First time setup (inside pod):"
echo "  init-workspace"
echo ""
echo "Start a new feature:"
echo "  thread new my-feature"
echo ""
echo "View proxy logs:"
echo "  kubectl logs -n $NAMESPACE -l app=egress-proxy -f"
