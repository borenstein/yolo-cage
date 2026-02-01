"""Host prerequisite checking."""

import shutil
import subprocess
import sys


def check() -> list[str]:
    """Check for required tools. Returns list of missing items."""
    missing = []
    is_macos = sys.platform == "darwin"

    if not shutil.which("vagrant"):
        missing.append("vagrant")

    if not shutil.which("git"):
        missing.append("git")

    if is_macos:
        result = subprocess.run(
            ["brew", "list", "--formula"],
            capture_output=True,
            text=True,
        )
        if "qemu" not in (result.stdout if result.returncode == 0 else ""):
            missing.append("qemu")

        if shutil.which("vagrant"):
            result = subprocess.run(
                ["vagrant", "plugin", "list"],
                capture_output=True,
                text=True,
            )
            if "vagrant-qemu" not in result.stdout:
                missing.append("vagrant-qemu plugin")
    else:
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


def print_install_help(missing: list[str]) -> None:
    """Print installation instructions for missing prerequisites."""
    print("Missing prerequisites:")
    for dep in missing:
        print(f"  - {dep}")
    print()
    print("Install with:")
    print()
    if sys.platform == "darwin":
        print("  brew install vagrant qemu")
        print("  vagrant plugin install vagrant-qemu")
    else:
        print("  Ubuntu/Debian:")
        print("    sudo apt install vagrant vagrant-libvirt qemu-kvm libvirt-daemon-system")
        print()
        print("  Fedora:")
        print("    sudo dnf install vagrant vagrant-libvirt qemu-kvm libvirt")
