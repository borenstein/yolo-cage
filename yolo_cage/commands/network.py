"""Network commands - port forwarding."""

import argparse
import subprocess

from ..output import die
from ..instances import (
    get_repo_dir,
    resolve_instance,
    maybe_migrate_legacy_layout,
)
from ..vm import ensure_vm_running


def cmd_port_forward(args: argparse.Namespace) -> None:
    """Forward a port from a sandbox pod to localhost."""
    maybe_migrate_legacy_layout()
    instance = resolve_instance(args.instance)
    repo_dir = get_repo_dir(instance)

    ensure_vm_running(repo_dir)

    # Parse port spec: "8080" or "local:remote"
    if ":" in args.port:
        local_port, pod_port = args.port.split(":", 1)
    else:
        local_port = pod_port = args.port

    # Validate ports are numeric
    try:
        int(local_port)
        int(pod_port)
    except ValueError:
        die(f"Invalid port specification: {args.port}")

    bind_addr = args.bind
    branch = args.branch
    pod_name = f"yolo-cage-{branch}"

    print(f"Forwarding {bind_addr}:{local_port} -> {pod_name}:{pod_port}")
    print("Press Ctrl+C to stop")
    print()

    # Use SSH tunnel (-L) combined with kubectl port-forward
    # The -L flag creates: host:local_port -> VM:local_port
    # kubectl port-forward creates: VM:local_port -> pod:pod_port
    kubectl_cmd = f"kubectl port-forward -n yolo-cage pod/{pod_name} {local_port}:{pod_port}"
    ssh_cmd = [
        "vagrant",
        "ssh",
        "--",
        "-L",
        f"{bind_addr}:{local_port}:localhost:{local_port}",
        kubectl_cmd,
    ]

    try:
        subprocess.call(ssh_cmd, cwd=repo_dir)
    except KeyboardInterrupt:
        print("\nPort forwarding stopped.")
