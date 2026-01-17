#!/bin/bash
# build-release.sh - Deterministic yolo-cage deployment from fresh Ubuntu VM
#
# This script takes a fresh Ubuntu 22.04 VM to a working yolo-cage installation.
# It is idempotent: running it multiple times produces the same result.
#
# Usage:
#   ./scripts/build-release.sh [--skip-microk8s] [--skip-images]
#
# Options:
#   --skip-microk8s   Skip MicroK8s installation (useful if already installed)
#   --skip-images     Skip image building (use existing images)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_phase() {
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}Phase: $1${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
}

log_step() {
    echo -e "${YELLOW}→ $1${NC}"
}

log_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

# Parse arguments
SKIP_MICROK8S=false
SKIP_IMAGES=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-microk8s)
            SKIP_MICROK8S=true
            shift
            ;;
        --skip-images)
            SKIP_IMAGES=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Detect script location and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "yolo-cage build-release.sh"
echo "=========================="
echo "Repo root: ${REPO_ROOT}"
echo ""

# ============================================================================
# Phase 1: System Prerequisites
# ============================================================================
log_phase "1. System Prerequisites"

log_step "Checking for Docker..."
if ! command -v docker &> /dev/null; then
    log_step "Installing Docker..."
    sudo apt-get update
    sudo apt-get install -y docker.io
    sudo usermod -aG docker "$USER"
    echo "Docker installed. You may need to log out and back in for group membership."
fi

log_step "Checking for jq..."
if ! command -v jq &> /dev/null; then
    log_step "Installing jq..."
    sudo apt-get update
    sudo apt-get install -y jq
fi

log_step "Checking for curl..."
if ! command -v curl &> /dev/null; then
    log_step "Installing curl..."
    sudo apt-get update
    sudo apt-get install -y curl
fi

echo "System prerequisites complete."

# ============================================================================
# Phase 2: MicroK8s Installation
# ============================================================================
log_phase "2. MicroK8s"

if [[ "$SKIP_MICROK8S" == "true" ]]; then
    log_step "Skipping MicroK8s installation (--skip-microk8s)"
else
    if ! command -v microk8s &> /dev/null; then
        log_step "Installing MicroK8s..."
        sudo snap install microk8s --classic
        sudo usermod -aG microk8s "$USER"
        echo "MicroK8s installed. You may need to log out and back in for group membership."
    fi

    log_step "Waiting for MicroK8s to be ready..."
    sudo microk8s status --wait-ready

    log_step "Enabling MicroK8s addons..."
    sudo microk8s enable dns
    sudo microk8s enable registry
    sudo microk8s enable hostpath-storage

    log_step "Waiting for addons to be ready..."
    sleep 10
    sudo microk8s status --wait-ready
fi

# Setup kubectl alias if not already done
if ! command -v kubectl &> /dev/null; then
    log_step "Setting up kubectl alias..."
    sudo snap alias microk8s.kubectl kubectl
fi

echo "MicroK8s setup complete."

# ============================================================================
# Phase 3: Build Images
# ============================================================================
log_phase "3. Build Images"

if [[ "$SKIP_IMAGES" == "true" ]]; then
    log_step "Skipping image building (--skip-images)"
else
    # Build dispatcher image
    log_step "Building git-dispatcher image..."
    docker build -t localhost:32000/git-dispatcher:latest \
        -f "${REPO_ROOT}/dockerfiles/dispatcher/Dockerfile" \
        "${REPO_ROOT}"

    log_step "Pushing git-dispatcher to local registry..."
    docker push localhost:32000/git-dispatcher:latest

    # Build sandbox image
    log_step "Building yolo-cage sandbox image..."
    docker build -t localhost:32000/yolo-cage:latest \
        -f "${REPO_ROOT}/dockerfiles/sandbox/Dockerfile" \
        "${REPO_ROOT}"

    log_step "Pushing yolo-cage to local registry..."
    docker push localhost:32000/yolo-cage:latest

    # Build proxy image
    log_step "Building egress-proxy image..."
    docker build -t localhost:32000/egress-proxy:latest \
        -f "${REPO_ROOT}/dockerfiles/proxy/Dockerfile" \
        "${REPO_ROOT}"

    log_step "Pushing egress-proxy to local registry..."
    docker push localhost:32000/egress-proxy:latest
fi

echo "Image building complete."

# ============================================================================
# Phase 4: Apply Manifests
# ============================================================================
log_phase "4. Apply Manifests"

log_step "Creating namespace..."
kubectl apply -f "${REPO_ROOT}/manifests/namespace.yaml"

log_step "Applying dispatcher RBAC..."
kubectl apply -n yolo-cage -f "${REPO_ROOT}/manifests/dispatcher/rbac.yaml"

log_step "Applying dispatcher configmap..."
kubectl apply -n yolo-cage -f "${REPO_ROOT}/manifests/dispatcher/configmap.yaml"

log_step "Applying sandbox PVC..."
kubectl apply -n yolo-cage -f "${REPO_ROOT}/manifests/sandbox/pvc.yaml"

log_step "Applying sandbox configmaps..."
kubectl apply -n yolo-cage -f "${REPO_ROOT}/manifests/sandbox/configmap.yaml"
kubectl apply -n yolo-cage -f "${REPO_ROOT}/manifests/sandbox/agent-prompt.yaml" || true

log_step "Applying proxy configmaps..."
kubectl apply -n yolo-cage -f "${REPO_ROOT}/manifests/proxy/configmap.yaml" || true

log_step "Applying network policy..."
kubectl apply -n yolo-cage -f "${REPO_ROOT}/manifests/sandbox/networkpolicy.yaml"

log_step "Applying egress proxy..."
kubectl apply -n yolo-cage -f "${REPO_ROOT}/manifests/proxy/egress-proxy.yaml"

log_step "Applying dispatcher service..."
kubectl apply -n yolo-cage -f "${REPO_ROOT}/manifests/dispatcher/service.yaml"

log_step "Applying dispatcher deployment..."
kubectl apply -n yolo-cage -f "${REPO_ROOT}/manifests/dispatcher/deployment.yaml"

log_step "Waiting for dispatcher to be ready..."
kubectl rollout status -n yolo-cage deployment/git-dispatcher --timeout=120s

echo "Manifests applied."

# ============================================================================
# Phase 5: Install CLI
# ============================================================================
log_phase "5. Install CLI"

log_step "Installing yolo-cage CLI..."
sudo cp "${REPO_ROOT}/scripts/yolo-cage" /usr/local/bin/yolo-cage
sudo chmod +x /usr/local/bin/yolo-cage

log_step "Installing yolo-cage-configure..."
if [[ -f "${REPO_ROOT}/scripts/yolo-cage-configure" ]]; then
    sudo cp "${REPO_ROOT}/scripts/yolo-cage-configure" /usr/local/bin/yolo-cage-configure
    sudo chmod +x /usr/local/bin/yolo-cage-configure
fi

echo "CLI installed."

# ============================================================================
# Phase 6: Generate Proxy CA
# ============================================================================
log_phase "6. Generate Proxy CA"

# Check if proxy-ca ConfigMap already exists
if kubectl get configmap -n yolo-cage proxy-ca &> /dev/null; then
    log_step "Proxy CA ConfigMap already exists, skipping generation"
else
    log_step "Generating mitmproxy CA certificate..."

    # Create temp directory for CA generation
    CA_TEMP=$(mktemp -d)
    trap "rm -rf ${CA_TEMP}" EXIT

    # Generate CA using openssl (same format as mitmproxy)
    openssl genrsa -out "${CA_TEMP}/mitmproxy-ca.key" 2048
    openssl req -new -x509 -key "${CA_TEMP}/mitmproxy-ca.key" \
        -out "${CA_TEMP}/mitmproxy-ca.pem" \
        -days 3650 \
        -subj "/CN=yolo-cage proxy CA/O=yolo-cage"

    log_step "Creating proxy-ca ConfigMap..."
    kubectl create configmap proxy-ca \
        -n yolo-cage \
        --from-file=mitmproxy-ca.pem="${CA_TEMP}/mitmproxy-ca.pem"

    # Also create the secret for the proxy to use (key + cert)
    log_step "Creating proxy-ca-secret..."
    kubectl create secret generic proxy-ca-secret \
        -n yolo-cage \
        --from-file=mitmproxy-ca.pem="${CA_TEMP}/mitmproxy-ca.pem" \
        --from-file=mitmproxy-ca.key="${CA_TEMP}/mitmproxy-ca.key" \
        || true  # Ignore if exists
fi

echo "Proxy CA setup complete."

# ============================================================================
# Done
# ============================================================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}yolo-cage installation complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure yolo-cage with your GitHub credentials:"
echo "   yolo-cage-configure"
echo ""
echo "2. Create your first pod:"
echo "   yolo-cage create my-feature-branch"
echo ""
echo "3. Attach to the pod:"
echo "   yolo-cage attach my-feature-branch"
echo ""
