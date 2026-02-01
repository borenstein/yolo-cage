"""Network commands - port forwarding."""

import argparse
import subprocess

from .. import instances, vagrant
from ...output import die


def cmd_port_forward(args: argparse.Namespace) -> None:
    """Forward a port from a sandbox to localhost."""
    instances.migrate_legacy()
    name = instances.resolve(args.instance)
    repo_dir = instances.get_repo_dir(name)

    if not (repo_dir / "Vagrantfile").exists():
        die(f"Repository not found for instance '{name}'.")

    vagrant.ensure_running(repo_dir)

    # Parse port spec
    if ":" in args.port:
        local_port, pod_port = args.port.split(":", 1)
    else:
        local_port = pod_port = args.port

    try:
        int(local_port)
        int(pod_port)
    except ValueError:
        die(f"Invalid port: {args.port}")

    pod_name = f"yolo-cage-{args.branch}"
    print(f"Forwarding {args.bind}:{local_port} -> {pod_name}:{pod_port}")
    print("Press Ctrl+C to stop")
    print()

    kubectl_cmd = f"kubectl port-forward -n yolo-cage pod/{pod_name} {local_port}:{pod_port}"
    ssh_cmd = [
        "vagrant", "ssh", "--",
        "-L", f"{args.bind}:{local_port}:localhost:{local_port}",
        kubectl_cmd,
    ]

    try:
        subprocess.call(ssh_cmd, cwd=repo_dir)
    except KeyboardInterrupt:
        print("\nStopped.")
