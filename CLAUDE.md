# yolo-cage

Sandboxed Claude Code agents. See [README.md](README.md) for full documentation.

## Development

### Prerequisites

- Vagrant with QEMU (macOS: `brew install vagrant qemu && vagrant plugin install vagrant-qemu`)
- Vagrant with libvirt (Linux: `sudo apt install vagrant vagrant-libvirt qemu-kvm libvirt-daemon-system`)
- 8GB RAM, 4 CPUs available for the VM
- Python 3.10+ for running tests

### Project structure

```
yolo_cage/              # Python package (CLI)
├── __init__.py         # Version constant
├── __main__.py         # Entry point
├── cli.py              # Argument parsing, command handlers
├── registry.py         # Registry - manages instances
├── instance.py         # Instance - a named environment
├── config.py           # Config - typed configuration
├── vm.py               # VM - Vagrant operations
├── output.py           # Logging helpers
├── github.py           # GitHub URL parsing, validation
├── prerequisites.py    # Platform detection, dependency checks
scripts/
├── build-zipapp.sh     # Build CLI as zipapp
├── yolo-cage           # Wrapper script (calls zipapp or package)
└── yolo-cage-*         # VM-side scripts
tests/                  # pytest tests
dist/
└── yolo-cage           # Built zipapp (generated)
```

### Building and testing

```bash
# Run tests
pip install pytest pytest-mock
pytest tests/ -v

# Build zipapp
./scripts/build-zipapp.sh dev
./dist/yolo-cage --version

# Full rebuild with VM
./dist/yolo-cage build --instance=dev --interactive --up
```

### Testing changes

```bash
# Build and test from local repo
./dist/yolo-cage build --instance=dev --interactive --up
./dist/yolo-cage -I dev create test-branch
./dist/yolo-cage -I dev attach test-branch
./dist/yolo-cage -I dev delete test-branch

# Or manual testing inside VM
vagrant ssh
yolo-cage-inner create test-branch
yolo-cage-inner list
yolo-cage-inner delete test-branch
```

### CI Requirements

The main branch must always build successfully:
1. `pytest tests/` passes
2. `./scripts/build-zipapp.sh` creates working zipapp
3. `vagrant up` completes without errors
4. `yolo-cage-configure` can apply a valid config
