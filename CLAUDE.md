# yolo-cage

Run Claude Code in a sandboxed Kubernetes environment with git branch isolation.

## Quick Start

```bash
vagrant up                    # Build the VM
vagrant ssh                   # Connect to VM
cp config.yaml.example ~/.yolo-cage/config.yaml
# Edit config.yaml with your credentials
yolo-cage-configure           # Apply configuration
yolo-cage create my-branch    # Create a sandbox
yolo-cage attach my-branch    # Connect to it
```

## Architecture

- **Vagrant VM**: Self-contained MicroK8s cluster
- **Dispatcher**: Manages git operations and pod lifecycle
- **Sandbox pods**: Isolated environments per branch
- **Egress proxy**: Filters outbound traffic

## Development

### Prerequisites

- Vagrant with libvirt provider (for headless servers) or VirtualBox
- 8GB RAM, 4 CPUs available for the VM

### Testing changes

```bash
vagrant destroy -f && vagrant up   # Full rebuild
vagrant ssh
yolo-cage-configure
yolo-cage create test-branch
yolo-cage list
yolo-cage delete test-branch
```

### CI Requirements

The main branch must always build successfully:
1. `vagrant up` completes without errors
2. `yolo-cage-configure` can apply a valid config
