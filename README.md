# yolo-cage: AI coding agents that can't exfiltrate secrets or merge their own PRs

I was running four Claude Code agents in parallel on different parts of a project, and losing my mind playing whack-a-mole with permission prompts. YOLO mode was the obvious answer. But I couldn't actually do it.

So I built the cage that makes it safe.

<p align="center">
  <img src="assets/escape-blocked.gif" width="600" alt="Escape attempts blocked">
</p>

## Try it

```bash
curl -fsSL https://github.com/borenstein/yolo-cage/releases/latest/download/yolo-cage -o yolo-cage
chmod +x yolo-cage && sudo mv yolo-cage /usr/local/bin/
yolo-cage build --interactive --up
```

Then create a sandbox and start coding:

```bash
yolo-cage create feature-branch
yolo-cage attach feature-branch   # Claude in tmux, YOLO mode
```

**Prerequisites:** Vagrant (libvirt or VirtualBox), 8GB RAM, 4 CPUs, GitHub PAT (`repo` scope), Claude account.

---

## What gets blocked

**Secrets in HTTP/HTTPS** - egress proxy scans request bodies, headers, URLs:
- `sk-ant-*`, `AKIA*`, `ghp_*`, SSH private keys, generic credential patterns

**Git operations** - dispatcher enforces branch isolation:
- Push to any branch except the one assigned at sandbox creation
- `git remote`, `git clone`, `git config`, `git credential`

**GitHub CLI** - dispatcher blocks dangerous commands:
- `gh pr merge`, `gh repo delete`, `gh api`

**GitHub API** - proxy blocks at HTTP layer:
- `PUT /repos/*/pulls/*/merge`, `DELETE /repos/*`, webhook modifications

**Exfiltration sites**: pastebin.com, file.io, transfer.sh, etc.

See [Architecture](docs/architecture.md) for the full threat model.

---

## How it works

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Vagrant VM (MicroK8s)                                                    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Sandbox Pod                                                        │  │
│  │                                                                    │  │
│  │  Claude Code (YOLO mode)                                           │  │
│  │       │                                                            │  │
│  │       ├── git/gh ──▶ Dispatcher ──▶ GitHub                         │  │
│  │       │              • Branch enforcement                          │  │
│  │       │              • TruffleHog pre-push                         │  │
│  │       │                                                            │  │
│  │       └── HTTP/S ──▶ Egress Proxy ──▶ Internet                     │  │
│  │                      • Secret scanning                             │  │
│  │                      • Domain blocklist                            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

One sandbox per branch. Agents can only push to their assigned branch. All outbound traffic is filtered.

---

## CLI

| Command | Description |
|---------|-------------|
| `create <branch>` | Create sandbox |
| `attach <branch>` | Attach (Claude in tmux) |
| `shell <branch>` | Attach (bash) |
| `list` | List sandboxes |
| `delete <branch>` | Delete sandbox |
| `up` / `down` | Start/stop VM |

See [Configuration](docs/configuration.md) for proxy bypass, hooks, and resource limits.

---

## Documentation

- **[Architecture](docs/architecture.md)** - Threat model, design rationale
- **[Configuration](docs/configuration.md)** - Egress policy, proxy bypass, hooks
- **[Customization](docs/customization.md)** - Adding tools, resource limits
- **[Security Audit](docs/security-audit.md)** - Escape testing guide

---

## Limitations

This reduces risk. It does not eliminate it.

- **DNS exfiltration** - data encoded in DNS queries
- **Timing side channels** - information leaked via response timing
- **Steganography** - secrets hidden in images or binary data
- **Sophisticated encoding** - bypassing pattern matching

Use scoped credentials. Don't use production secrets where exfiltration would be catastrophic. See [Security Audit](docs/security-audit.md) to test it yourself.

<!-- TODO: Add links to security PRs once available -->

---

## License

MIT. See [LICENSE](LICENSE).
