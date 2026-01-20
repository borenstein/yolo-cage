# yolo-cage

Sandboxed Claude Code agents. See [README.md](README.md) for full documentation.

## Development

### Prerequisites

- Vagrant with libvirt provider (macOS: `brew install vagrant libvirt qemu && vagrant plugin install vagrant-libvirt`)
- 8GB RAM, 4 CPUs available for the VM

### Testing changes

```bash
# Full rebuild from repo root
./scripts/yolo-cage build

# Or manual testing inside VM
vagrant destroy -f && vagrant up
vagrant ssh
cp /home/vagrant/yolo-cage/config.env.example ~/.yolo-cage/config.env
# Edit config.env with your credentials
yolo-cage-configure
yolo-cage-inner create test-branch
yolo-cage-inner list
yolo-cage-inner delete test-branch
```

### CI Requirements

The main branch must always build successfully:
1. `vagrant up` completes without errors
2. `yolo-cage-configure` can apply a valid config
