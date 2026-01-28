"""Prerequisite checking for yolo-cage."""

import shutil
import subprocess
import sys


def check_prerequisites() -> None:
    """Verify required tools are installed."""
    missing = []
    is_macos = sys.platform == "darwin"

    if not shutil.which("vagrant"):
        missing.append("vagrant")

    if not shutil.which("git"):
        missing.append("git")

    if is_macos:
        # macOS requires QEMU + vagrant-qemu plugin
        result = subprocess.run(
            ["brew", "list", "--formula"],
            capture_output=True,
            text=True,
        )
        installed_formulas = result.stdout if result.returncode == 0 else ""
        if "qemu" not in installed_formulas:
            missing.append("qemu")

        # Check for vagrant-qemu plugin
        if shutil.which("vagrant"):
            result = subprocess.run(
                ["vagrant", "plugin", "list"],
                capture_output=True,
                text=True,
            )
            if "vagrant-qemu" not in result.stdout:
                missing.append("vagrant-qemu plugin")
    else:
        # On Linux, check for libvirtd or VirtualBox
        has_vbox = shutil.which("VBoxManage") is not None
        has_libvirt = shutil.which("libvirtd") is not None
        if not has_libvirt and not has_vbox:
            missing.append("libvirt (or VirtualBox)")

        # Check for vagrant-libvirt plugin if using libvirt
        if shutil.which("vagrant") and has_libvirt:
            result = subprocess.run(
                ["vagrant", "plugin", "list"],
                capture_output=True,
                text=True,
            )
            if "vagrant-libvirt" not in result.stdout:
                missing.append("vagrant-libvirt plugin")

    if missing:
        print("Missing prerequisites:")
        for dep in missing:
            print(f"  - {dep}")
        print()
        print("Install with:")
        print()
        if is_macos:
            print("  macOS:")
            print("    brew install vagrant qemu")
            print("    vagrant plugin install vagrant-qemu")
        else:
            print("  Ubuntu/Debian:")
            print("    sudo apt install vagrant vagrant-libvirt qemu-kvm libvirt-daemon-system")
            print()
            print("  Fedora:")
            print("    sudo dnf install vagrant vagrant-libvirt qemu-kvm libvirt")
        sys.exit(1)
