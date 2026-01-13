# Architecture

> **Disclaimer**: This was built to solve a specific problem (running Claude Code in YOLO mode without babysitting). It reduces risk but does not eliminate it. See [LICENSE](../LICENSE) for warranty disclaimers. Do not use with production secrets or credentials where exfiltration would be catastrophic.

## The Goal

Run N [Claude Code](https://docs.anthropic.com/en/docs/claude-code) agents in parallel, each working on a different feature branch, without:
- Babysitting permission prompts
- Worrying about credential exfiltration
- Giving up on autonomous operation

## The Threat Model

### The "Lethal Trifecta"

[Simon Willison](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) identified the "lethal trifecta" for AI agents: access to private data, exposure to untrusted content, and the ability to exfiltrate externally. When all three are present, prompt injection and other attacks become exploitable.

For AI coding agents specifically:

| Capability | Why Needed | Risk |
|------------|-----------|------|
| Internet access | Docs, APIs, package registries, web search | Exfiltration channel |
| Code execution | That's the whole point | Can access filesystem, env vars |
| Secrets | API keys, SSH keys, credentials | The payload worth stealing |

Any two are manageable. A sandboxed REPL with no network is safe. An internet-connected browser with no code execution is safe. A code executor with secrets but no network is safe.

All three together means: the agent can read your secrets and send them anywhere.

### Why Permission Prompts Don't Scale

Claude Code's permission system exists because of this risk. Every network request, file write, or command execution gets a prompt: "Allow this?"

This is fine for a single interactive session. It breaks down when you want:
- Multiple agents working in parallel
- Autonomous overnight runs
- Reduced friction for trusted operations

YOLO mode (`--dangerously-skip-permissions`) removes the prompts but also removes the guardrails.

## The Solution: Container Isolation + Egress Filtering

The solution combines two layers:

1. **Container isolation**: The agent runs inside a Kubernetes pod with restricted privileges—non-root user, no host access, isolated filesystem. This is strong sandboxing at the OS level.

2. **Egress filtering**: All network traffic passes through a scanning proxy that blocks secrets from leaving. This addresses the exfiltration leg of the trifecta.

### Key Insight

Inside the container, the agent can do whatever it wants:
- Read any file in the workspace
- Execute any code
- Access any mounted secret or environment variable

But it cannot send data out without going through the egress proxy. And the proxy scans everything for secrets before forwarding.

The container boundary is the sandboxing. The proxy is the exfiltration control.

### Components

#### 1. yolo-cage Container
The Claude Code development environment:
- Python 3.12 + Node.js 22 (full-stack development)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [tmux](https://github.com/tmux/tmux/wiki) (session persistence across disconnects)
- Git with [worktree](https://git-scm.com/docs/git-worktree) support for parallel branches

Runs as non-root user (UID 1000). Workspace persisted via Kubernetes PVC.

#### 2. Egress Proxy ([mitmproxy](https://mitmproxy.org/))
HTTPS-intercepting proxy that:
- Terminates TLS (using its own CA certificate)
- Passes request bodies to LLM-Guard for scanning
- Blocks requests containing detected secrets
- Blocks requests to known exfiltration domains
- Logs all traffic for audit

#### 3. [LLM-Guard](https://github.com/protectai/llm-guard)
Protect AI's security toolkit running as a sidecar service:
- Uses [detect-secrets](https://github.com/Yelp/detect-secrets) library (originally from Yelp)
- Pattern matching for known credential formats
- Heuristic detection for high-entropy strings
- Returns pass/fail verdict to proxy

#### 4. NetworkPolicy
Kubernetes-native egress restrictions:
- yolo-cage can only reach: DNS, egress-proxy, SSH (for git)
- Egress-proxy can reach: DNS, LLM-Guard, internet
- LLM-Guard has no egress (it's a pure scanner)

## Traffic Flows

### HTTP/HTTPS Requests
```
yolo-cage container
    │
    │ HTTP_PROXY=http://egress-proxy:8080
    ▼
egress-proxy (mitmproxy)
    │
    │ POST /analyze/prompt
    ▼
LLM-Guard ──────▶ {is_valid: true}  ──▶ Forward to internet
    │
    └──────────▶ {is_valid: false} ──▶ Return 403 Forbidden
```

### Git over SSH
```
yolo-cage container
    │
    │ Direct (bypasses proxy)
    ▼
github.com:22
```

SSH traffic is not scanned. See "Known Limitations" below.

## What Gets Blocked

### Credential Patterns (Regex)
- `sk-ant-*` - Anthropic API keys
- `AKIA[0-9A-Z]{16}` - AWS access keys
- `ghp_[a-zA-Z0-9]{36}` - GitHub personal access tokens
- `github_pat_*` - GitHub fine-grained tokens
- `-----BEGIN * PRIVATE KEY-----` - SSH/TLS private keys

### Heuristic Detection (detect-secrets)
- High-entropy base64 strings
- Hex strings that look like tokens
- Keyword proximity ("password", "secret", "token" near suspicious values)

### Domain Blocklist
Paste sites: `pastebin.com`, `paste.ee`, `hastebin.com`, `dpaste.org`
File sharing: `file.io`, `transfer.sh`, `0x0.st`, `ix.io`, `sprunge.us`, `termbin.com`

## Known Limitations

### SSH Bypass
Git over SSH goes direct to GitHub, bypassing the proxy entirely. Possible exfiltration vectors:
- Commit messages
- Branch names
- File contents pushed to a repo the agent controls

**Mitigations:**
- Use a deploy key with read-only access
- Use git-over-HTTPS instead (proxied and scanned)
- Accept this as a residual risk (the agent would need to be explicitly adversarial)

### Prompt Injection
The egress filter mitigates many prompt injection attacks—even if a malicious file tricks the agent into attempting exfiltration, the secrets get blocked at the network layer.

However, sophisticated attacks could still bypass scanning:
- Encoding secrets in URL paths rather than bodies
- Using DNS exfiltration
- Steganography in image requests

**Mitigations:**
- The egress filter catches the obvious cases
- DNS can be locked down to known resolvers
- At some point, you're defending against a sophisticated attacker, not an accident

### Fail-Open Default
If LLM-Guard is unavailable, the proxy logs a warning and allows the request. This prioritizes availability over security.

To change to fail-closed, modify `secret_scanner.py`:
```python
# Current (fail-open)
if not self.llm_guard_available:
    logger.warning("LLM-Guard unavailable, allowing request")
    return False, []

# Fail-closed alternative
if not self.llm_guard_available:
    logger.error("LLM-Guard unavailable, blocking request")
    return True, ["scanner_unavailable"]
```

### Not a Security Boundary
This setup reduces risk; it does not eliminate it. Do not use it for:
- Production secrets
- Credentials with broad access
- Anything where exfiltration would be catastrophic

Use scoped credentials (deploy keys, limited API tokens) and treat the sandbox as defense-in-depth, not a fortress.
