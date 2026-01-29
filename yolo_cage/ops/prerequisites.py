"""Prerequisite detection for yolo-cage."""

import shutil
import subprocess
import sys


def check_dependencies() -> list[str]:
    """Return list of missing dependencies (empty if all present)."""
    missing = []
    missing.extend(_check_common())
    if sys.platform == "darwin":
        missing.extend(_check_macos())
    else:
        missing.extend(_check_linux())
    return missing


def _check_common() -> list[str]:
    """Check dependencies needed on all platforms."""
    missing = []
    if not shutil.which("vagrant"):
        missing.append("vagrant")
    if not shutil.which("git"):
        missing.append("git")
    return missing


def _check_macos() -> list[str]:
    """Check macOS-specific dependencies."""
    missing = []

    result = subprocess.run(
        ["brew", "list", "--formula"],
        capture_output=True,
        text=True,
    )
    installed = result.stdout if result.returncode == 0 else ""
    if "qemu" not in installed:
        missing.append("qemu")

    if shutil.which("vagrant"):
        result = subprocess.run(
            ["vagrant", "plugin", "list"],
            capture_output=True,
            text=True,
        )
        if "vagrant-qemu" not in result.stdout:
            missing.append("vagrant-qemu plugin")

    return missing


def _check_linux() -> list[str]:
    """Check Linux-specific dependencies."""
    missing = []

    has_vbox = shutil.which("VBoxManage") is not None
    has_libvirt = shutil.which("libvirtd") is not None

    if not has_libvirt and not has_vbox:
        missing.append("libvirt (or VirtualBox)")

    if shutil.which("vagrant") and has_libvirt:
        result = subprocess.run(
            ["vagrant", "plugin", "list"],
            capture_output=True,
            text=True,
        )
        if "vagrant-libvirt" not in result.stdout:
            missing.append("vagrant-libvirt plugin")

    return missing


def format_install_instructions(missing: list[str]) -> str:
    """Generate installation instructions for missing dependencies."""
    lines = ["Missing prerequisites:"]
    for dep in missing:
        lines.append(f"  - {dep}")
    lines.append("")
    lines.append("Install with:")
    lines.append("")

    if sys.platform == "darwin":
        lines.append("  macOS:")
        lines.append("    brew install vagrant qemu")
        lines.append("    vagrant plugin install vagrant-qemu")
    else:
        lines.append("  Ubuntu/Debian:")
        lines.append("    sudo apt install vagrant vagrant-libvirt qemu-kvm libvirt-daemon-system")
        lines.append("")
        lines.append("  Fedora:")
        lines.append("    sudo dnf install vagrant vagrant-libvirt qemu-kvm libvirt")

    return "\n".join(lines)
