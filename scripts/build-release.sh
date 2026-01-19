#!/bin/bash
# build-release.sh - Provision a yolo-cage environment
#
# Called by Vagrant during `vagrant up`. Installs MicroK8s, builds container
# images, deploys manifests, and installs the CLI tools.
#
# Prerequisites: Fresh Ubuntu 22.04 VM with this repo synced to /home/vagrant/yolo-cage

set -e

# Locate repo root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "========================================"
echo "yolo-cage build-release.sh"
echo "========================================"
echo "Repo: ${REPO_ROOT}"
echo ""

# ============================================================================
# Phase 1: System packages
# ============================================================================
echo "Phase 1: System packages"

sudo apt-get update
sudo apt-get install -y docker.io jq curl openssl

# Add vagrant user to docker group
sudo usermod -aG docker vagrant

echo "System packages installed."

# ============================================================================
# Phase 2: MicroK8s
# ============================================================================
echo ""
echo "Phase 2: MicroK8s"

# Wait for snapd to be ready
echo "Waiting for snapd to be ready..."
sudo snap wait system seed.loaded

sudo snap install microk8s --classic
sudo usermod -aG microk8s vagrant

# Wait for microk8s to be ready
sudo microk8s status --wait-ready

# Enable required addons
sudo microk8s enable dns
sudo microk8s enable registry
sudo microk8s enable hostpath-storage

# Wait for addons
sleep 10
sudo microk8s status --wait-ready

# Setup kubectl alias
sudo snap alias microk8s.kubectl kubectl

echo "MicroK8s installed and configured."

# ============================================================================
# Phase 3: Build and push images
# ============================================================================
echo ""
echo "Phase 3: Build images"

# Need to use sg to get docker group membership in this session
sg docker -c "docker build -t localhost:32000/git-dispatcher:latest -f ${REPO_ROOT}/dockerfiles/dispatcher/Dockerfile ${REPO_ROOT}"
sg docker -c "docker push localhost:32000/git-dispatcher:latest"

sg docker -c "docker build -t localhost:32000/yolo-cage:latest -f ${REPO_ROOT}/dockerfiles/sandbox/Dockerfile ${REPO_ROOT}"
sg docker -c "docker push localhost:32000/yolo-cage:latest"

sg docker -c "docker build -t localhost:32000/egress-proxy:latest -f ${REPO_ROOT}/dockerfiles/proxy/Dockerfile ${REPO_ROOT}"
sg docker -c "docker push localhost:32000/egress-proxy:latest"

echo "Images built and pushed to local registry."

# ============================================================================
# Phase 4: Apply manifests
# ============================================================================
echo ""
echo "Phase 4: Apply manifests"

# Use microk8s.kubectl directly since alias may not be available yet
KUBECTL="sudo microk8s.kubectl"

$KUBECTL apply -f "${REPO_ROOT}/manifests/namespace.yaml"
$KUBECTL apply -n yolo-cage -f "${REPO_ROOT}/manifests/dispatcher/rbac.yaml"
$KUBECTL apply -n yolo-cage -f "${REPO_ROOT}/manifests/dispatcher/configmap.yaml"
$KUBECTL apply -n yolo-cage -f "${REPO_ROOT}/manifests/sandbox/pvc.yaml"
$KUBECTL apply -n yolo-cage -f "${REPO_ROOT}/manifests/sandbox/configmap.yaml"
$KUBECTL apply -n yolo-cage -f "${REPO_ROOT}/manifests/sandbox/networkpolicy.yaml"
$KUBECTL apply -n yolo-cage -f "${REPO_ROOT}/manifests/proxy/configmap.yaml"
$KUBECTL apply -n yolo-cage -f "${REPO_ROOT}/manifests/proxy/llm-guard.yaml"
$KUBECTL apply -n yolo-cage -f "${REPO_ROOT}/manifests/proxy/egress-proxy.yaml"
$KUBECTL apply -n yolo-cage -f "${REPO_ROOT}/manifests/dispatcher/service.yaml"
$KUBECTL apply -n yolo-cage -f "${REPO_ROOT}/manifests/dispatcher/deployment.yaml"

# Wait for dispatcher
$KUBECTL rollout status -n yolo-cage deployment/git-dispatcher --timeout=120s

echo "Manifests applied."

# ============================================================================
# Phase 5: Generate proxy CA
# ============================================================================
echo ""
echo "Phase 5: Generate proxy CA"

CA_TEMP=$(mktemp -d)

openssl genrsa -out "${CA_TEMP}/mitmproxy-ca.key" 2048
openssl req -new -x509 -key "${CA_TEMP}/mitmproxy-ca.key" \
    -out "${CA_TEMP}/mitmproxy-ca-cert.pem" \
    -days 3650 \
    -subj "/CN=yolo-cage proxy CA/O=yolo-cage"

# mitmproxy expects cert+key combined in mitmproxy-ca.pem
cat "${CA_TEMP}/mitmproxy-ca-cert.pem" "${CA_TEMP}/mitmproxy-ca.key" > "${CA_TEMP}/mitmproxy-ca.pem"

# ConfigMap for clients (cert only)
$KUBECTL create configmap proxy-ca \
    -n yolo-cage \
    --from-file=mitmproxy-ca.pem="${CA_TEMP}/mitmproxy-ca-cert.pem"

# Secret for proxy (combined cert+key and cert-only for mitmproxy)
$KUBECTL create secret generic proxy-ca-secret \
    -n yolo-cage \
    --from-file=mitmproxy-ca.pem="${CA_TEMP}/mitmproxy-ca.pem" \
    --from-file=mitmproxy-ca-cert.pem="${CA_TEMP}/mitmproxy-ca-cert.pem"

rm -rf "${CA_TEMP}"

echo "Proxy CA generated."

# ============================================================================
# Phase 6: Install CLI
# ============================================================================
echo ""
echo "Phase 6: Install CLI"

sudo cp "${REPO_ROOT}/scripts/yolo-cage-inner" /usr/local/bin/yolo-cage-inner
sudo chmod +x /usr/local/bin/yolo-cage-inner

sudo cp "${REPO_ROOT}/scripts/yolo-cage-configure" /usr/local/bin/yolo-cage-configure
sudo chmod +x /usr/local/bin/yolo-cage-configure

echo "CLI installed."

# ============================================================================
# Done
# ============================================================================
echo ""
echo "========================================"
echo "yolo-cage build complete!"
echo "========================================"
echo ""
echo "Next: Run 'yolo-cage-configure' to set up your credentials."
echo ""
