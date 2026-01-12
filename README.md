# yolo-cage: Kubernetes sandbox for Claude Code in YOLO mode

> **Disclaimer**: This was rigged up to solve a specific problem. It reduces risk but does not eliminate it. Do not use with production secrets or credentials where exfiltration would be catastrophic. See the [license](#license) section below.

A Kubernetes sandbox for running [Claude Code](https://docs.anthropic.com/en/docs/claude-code) in YOLO mode (`--dangerously-skip-permissions`) with egress filtering to prevent secret exfiltration.

## The Problem

You want multiple AI agents working on your codebase in parallel, each on different feature branches, without babysitting permission prompts. But YOLO mode feels irresponsible because agents have what [Simon Willison calls the "lethal trifecta"](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/):

1. **Internet access** (docs, APIs, package registries)
2. **Code execution** (the whole point)
3. **Secrets** (API keys, SSH keys, credentials)

Any two are fine. All three create exfiltration risk.

## The Solution

Two layers of containment:

1. **Container isolation**: The agent runs in a Kubernetes pod with restricted privileges—non-root user, isolated filesystem, no host access. This is strong OS-level sandboxing.

2. **Egress filtering**: All HTTP/HTTPS traffic passes through a scanning proxy. The proxy uses [LLM-Guard](https://github.com/protectai/llm-guard) (with [detect-secrets](https://github.com/Yelp/detect-secrets)) to block requests containing credentials.

The agent can do whatever it wants inside the container. It just can't send secrets out.

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│ Kubernetes Cluster                                         │
│                                                            │
│  ┌─────────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │  yolo-cage pod  │──▶│ egress-proxy │──▶│  LLM-Guard  │  │
│  │                 │   │  (mitmproxy) │   │             │  │
│  │  Claude Code    │   └──────┬───────┘   └─────────────┘  │
│  │  (YOLO mode)    │          │                            │
│  │                 │          ▼                            │
│  └────────┬────────┘   ┌──────────────┐                    │
│           │            │   Internet   │ (if clean)         │
│           └───SSH─────▶│   + GitHub   │                    │
|                        └──────────────┘                    |
└────────────────────────────────────────────────────────────┘
```

**What gets blocked:**
- Anthropic API keys (`sk-ant-*`)
- AWS credentials (`AKIA*`)
- GitHub tokens (`ghp_*`, `github_pat_*`)
- SSH private keys
- Generic secrets (via detect-secrets heuristics)
- Paste sites (pastebin.com, hastebin.com, etc.)
- File sharing (file.io, transfer.sh, 0x0.st, etc.)

## Quick Start

See [docs/setup.md](docs/setup.md) for detailed instructions. The short version:

```bash
# 1. Clone this repo
git clone https://github.com/borenstein/yolo-cage.git
cd yolo-cage

# 2. Edit configuration
cp manifests/config.example.yaml manifests/config.yaml
# Edit with your namespace, repo URL, registry, etc.

# 3. Create your secrets (see docs/setup.md)
# - GitHub deploy key
# - Claude OAuth credentials

# 4. Build and deploy
./deploy.sh

# 5. Get into the pod and start working
kubectl exec -it -n <namespace> deployment/yolo-cage -- bash
init-workspace
thread new my-feature
```

## Documentation

- [Architecture](docs/architecture.md) - Why this approach, threat model, limitations
- [Setup](docs/setup.md) - Prerequisites, step-by-step deployment
- [Customization](docs/customization.md) - Adapting for your project and cluster

## Workflow: Parallel Development with Worktrees

Each feature gets its own git worktree and tmux session:

```bash
thread new feature-auth        # Create worktree, start tmux session with Claude
thread new feature-api main    # Branch from specific ref
thread ls                      # List active worktrees and sessions
thread rm feature-auth         # Clean up when done
```

Multiple features can run in parallel. Detach with `Ctrl-b d`, reattach with `tmux attach -t feature-name`.

### First-Turn Prompts

Optionally, create `scripts/thread.first-turn.txt` to automatically orient new agents. This prompt runs when a thread starts, useful for ensuring agents review docs, run setup, and report the current commit SHA before you begin. See [docs/customization.md](docs/customization.md#first-turn-prompts).

### Restricting GitHub CLI Access

You may want agents to read issues for context without being able to merge PRs or modify repo settings. Use a fine-grained personal access token scoped to issues only. See [docs/customization.md](docs/customization.md#restricting-github-cli-access).

## Known Limitations

- **SSH bypasses the proxy**: Git over SSH goes direct. Secrets could theoretically be exfiltrated via commit messages or branch names. Mitigation: use git-over-HTTPS, or accept this risk.
- **Prompt injection**: The egress filter mitigates many prompt injection attacks—even if a malicious file tricks the agent into attempting exfiltration, the secrets get blocked at the network layer. However, sophisticated attacks (DNS exfiltration, steganography, encoding secrets in URL paths) could still bypass scanning.
- **Fail-open by default**: If LLM-Guard is down, requests pass through (with warnings). Change this in `secret_scanner.py` if you want fail-closed.

## Requirements

- Kubernetes cluster (developed on MicroK8s; may need adaptation for others)
- Container registry accessible from the cluster
- Docker (for building images)
- [Claude](https://claude.ai) account with OAuth credentials

## License

MIT. See [LICENSE](LICENSE) for full text.

**Important**: This software is provided "as is", without warranty of any kind. From the license:

> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

## Credits

Built by David Bruce Borenstein and Claude. The agent designed and implemented its own containment infrastructure, which is either very aligned or very meta, depending on your perspective.
