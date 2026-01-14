#!/bin/bash
# Deploy yolo-cage to your Kubernetes cluster
#
# Prerequisites:
# 1. kubectl configured for your cluster
# 2. Docker installed for building images
# 3. Secrets created (see docs/setup.md Steps 3-4)
# 4. Manifests configured (see docs/setup.md Step 5)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFESTS_DIR="${SCRIPT_DIR}/manifests"

# Parse namespace from namespace.yaml
NAMESPACE=$(grep "name:" "${MANIFESTS_DIR}/namespace.yaml" | head -1 | awk '{print $2}')

if [[ -z "$NAMESPACE" ]]; then
    echo -e "${RED}Error: Could not parse namespace from manifests/namespace.yaml${NC}"
    exit 1
fi

echo -e "${GREEN}=== yolo-cage Deployment ===${NC}"
echo "Namespace: $NAMESPACE"
echo ""

# Check if secrets exist
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
    echo "Creating namespace ${NAMESPACE}..."
    kubectl apply -f "${MANIFESTS_DIR}/namespace.yaml"
fi

if ! kubectl get secret github-pat -n "$NAMESPACE" &>/dev/null; then
    echo -e "${RED}Error: Secret 'github-pat' not found in namespace '$NAMESPACE'${NC}"
    echo "Create it with:"
    echo "  kubectl create secret generic github-pat \\"
    echo "    --namespace=$NAMESPACE \\"
    echo "    --from-literal=GITHUB_PAT=ghp_your_token_here"
    exit 1
fi

if ! kubectl get secret yolo-cage-credentials -n "$NAMESPACE" &>/dev/null; then
    echo -e "${RED}Error: Secret 'yolo-cage-credentials' not found in namespace '$NAMESPACE'${NC}"
    echo "Create it with:"
    echo "  kubectl create secret generic yolo-cage-credentials \\"
    echo "    --namespace=$NAMESPACE \\"
    echo "    --from-file=claude-oauth-credentials=./credentials.json"
    exit 1
fi

if ! kubectl get configmap proxy-ca -n "$NAMESPACE" &>/dev/null; then
    echo -e "${RED}Error: ConfigMap 'proxy-ca' not found in namespace '$NAMESPACE'${NC}"
    echo "Create it with:"
    echo "  openssl genrsa -out ca-key.pem 4096"
    echo "  openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem -subj '/CN=yolo-cage-proxy-ca'"
    echo "  kubectl create configmap proxy-ca --namespace=$NAMESPACE --from-file=mitmproxy-ca.pem=ca-cert.pem"
    exit 1
fi

echo -e "${GREEN}Prerequisites OK${NC}"
echo ""

# Apply manifests in order
echo -e "${YELLOW}Applying dispatcher manifests...${NC}"
kubectl apply -f "${MANIFESTS_DIR}/dispatcher/"

echo -e "${YELLOW}Applying proxy manifests...${NC}"
# Apply proxy configmap and deployments, but not proxy-ca.yaml (user creates manually)
kubectl apply -f "${MANIFESTS_DIR}/proxy/configmap.yaml"
kubectl apply -f "${MANIFESTS_DIR}/proxy/egress-proxy.yaml"
kubectl apply -f "${MANIFESTS_DIR}/proxy/llm-guard.yaml"

echo -e "${YELLOW}Applying sandbox manifests...${NC}"
# Apply everything except pod-template.yaml (used by CLI, not applied directly)
kubectl apply -f "${MANIFESTS_DIR}/sandbox/configmap.yaml"
kubectl apply -f "${MANIFESTS_DIR}/sandbox/agent-prompt.yaml"
kubectl apply -f "${MANIFESTS_DIR}/sandbox/networkpolicy.yaml"
kubectl apply -f "${MANIFESTS_DIR}/sandbox/pvc.yaml"

# Wait for deployments
echo ""
echo -e "${YELLOW}Waiting for git-dispatcher...${NC}"
kubectl rollout status -n "$NAMESPACE" deployment/git-dispatcher --timeout=120s

echo -e "${YELLOW}Waiting for egress-proxy...${NC}"
kubectl rollout status -n "$NAMESPACE" deployment/egress-proxy --timeout=120s

echo -e "${YELLOW}Waiting for llm-guard (this may take a while on first deploy)...${NC}"
kubectl rollout status -n "$NAMESPACE" deployment/llm-guard --timeout=300s || {
    echo -e "${YELLOW}Warning: LLM-Guard may still be loading models${NC}"
}

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Create a sandbox pod:"
echo "  yolo-cage create feature-name"
echo ""
echo "Or use the CLI from this repo:"
echo "  ./scripts/yolo-cage create feature-name"
echo ""
