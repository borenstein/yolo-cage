#!/bin/bash
# yolo-cage prerequisite cleanup script
# Use this to test the prerequisite check from various states

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "yolo-cage prerequisite cleanup"
echo "=============================="
echo ""
echo "What would you like to remove?"
echo ""
echo "  1) vagrant-libvirt plugin only (quick test)"
echo "  2) vagrant-libvirt + libvirt/qemu (test full macOS flow)"
echo "  3) Everything (vagrant + libvirt + qemu)"
echo "  4) Cancel"
echo ""
read -p "Choice [1-4]: " choice

case $choice in
  1)
    echo -e "${YELLOW}Removing vagrant-libvirt plugin...${NC}"
    vagrant plugin uninstall vagrant-libvirt || true
    echo -e "${GREEN}Done. Run 'yolo-cage build --interactive' to test plugin detection.${NC}"
    ;;
  2)
    echo -e "${YELLOW}Removing vagrant-libvirt plugin...${NC}"
    vagrant plugin uninstall vagrant-libvirt || true
    echo -e "${YELLOW}Removing libvirt and qemu...${NC}"
    brew uninstall --ignore-dependencies libvirt qemu || true
    echo -e "${GREEN}Done. Run 'yolo-cage build --interactive' to test libvirt detection.${NC}"
    ;;
  3)
    echo -e "${YELLOW}Removing vagrant-libvirt plugin...${NC}"
    vagrant plugin uninstall vagrant-libvirt || true
    echo -e "${YELLOW}Removing libvirt and qemu...${NC}"
    brew uninstall --ignore-dependencies libvirt qemu || true
    echo -e "${YELLOW}Removing vagrant...${NC}"
    brew uninstall --cask vagrant || true
    echo -e "${GREEN}Done. Run 'yolo-cage build --interactive' to test full detection.${NC}"
    ;;
  4)
    echo "Cancelled."
    exit 0
    ;;
  *)
    echo "Invalid choice"
    exit 1
    ;;
esac
