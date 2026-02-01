# yolo-cage

Sandboxed Claude Code [agents](docs/glossary.md#agent). See [README.md](README.md) for full documentation and [glossary](docs/glossary.md) for terminology.

## Development

### Prerequisites

- Vagrant with QEMU (macOS: `brew install vagrant qemu && vagrant plugin install vagrant-qemu`)
- 8GB RAM, 4 CPUs available for the [runtime](docs/glossary.md#runtime)

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
yolo-cage create test-branch
yolo-cage list
yolo-cage delete test-branch
```

### CI Requirements

The main branch must always build successfully:
1. `vagrant up` completes without errors
2. `yolo-cage-configure` can apply a valid [configuration](docs/glossary.md#configuration)
