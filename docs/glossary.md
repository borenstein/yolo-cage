# Glossary

This glossary defines the ubiquitous language used throughout the yolo-cage project. All documentation, code, and communication should use these terms consistently.

---

## Core Concepts

### <a name="runtime"></a>Runtime

The complete yolo-cage infrastructure, consisting of:
- The Vagrant VM
- The Kubernetes (MicroK8s) cluster
- The dispatcher service
- The egress proxy service
- Supporting services (LLM-Guard, container registry)

**Usage:** Users "build the runtime", "start the runtime", "upgrade the runtime"

**Related:** [VM](#vm), [Dispatcher](#dispatcher), [Egress Proxy](#egress-proxy)

---

### <a name="sandbox"></a>Sandbox

An isolated environment bound to a specific branch of the managed repository. A sandbox:
- Provides workspace isolation for an agent
- Enforces branch restrictions through the dispatcher
- Contains a clone of the managed repository
- Persists across sessions until explicitly deleted

**Implementation Note:** A sandbox is implemented as a Kubernetes pod, but users interact with the domain concept of a "sandbox", not the implementation detail of a "pod".

**Usage:** "Create a sandbox for the feature-x branch", "List all sandboxes", "Delete a sandbox"

**Related:** [Agent](#agent), [Assigned Branch](#assigned-branch), [Workspace](#workspace), [Pod](#pod)

---

### <a name="agent"></a>Agent

The autonomous AI (Claude Code running in YOLO mode) operating within a sandbox. An agent:
- Can read and write files in the workspace
- Has git operations intercepted by the dispatcher
- Has network traffic filtered by the egress proxy
- Operates under branch isolation constraints

**Usage:** "The agent pushes commits", "An agent operates within a sandbox"

**Related:** [Sandbox](#sandbox), [Workspace](#workspace)

---

### <a name="managed-repository"></a>Managed Repository

The GitHub repository that agents work on. This is the user's project repository configured in `config.env` via `REPO_URL`.

**Distinction:** This is different from the [System Repository](#system-repository), which contains yolo-cage's own code.

**Usage:** "Clone the managed repository into the sandbox", "The agent can only push to the managed repository's assigned branch"

**Related:** [System Repository](#system-repository), [Assigned Branch](#assigned-branch)

---

### <a name="system-repository"></a>System Repository

The GitHub repository containing yolo-cage's own codebase (`https://github.com/borenstein/yolo-cage`).

**Distinction:** This is different from the [Managed Repository](#managed-repository), which is the user's project that agents work on.

**Usage:** "Clone the system repository during build", "Upgrade pulls the latest system repository"

**Related:** [Managed Repository](#managed-repository)

---

### <a name="assigned-branch"></a>Assigned Branch

The specific git branch that a sandbox is created for and restricted to. An agent operating in a sandbox can only push commits to the assigned branch.

**Enforcement:** The dispatcher verifies all push operations target the assigned branch. Attempts to push to other branches are blocked.

**Usage:** "Create a sandbox for the feature-x branch", "The agent can only push to its assigned branch"

**Related:** [Sandbox](#sandbox), [Dispatcher](#dispatcher), [Branch Isolation](#branch-isolation)

---

### <a name="workspace"></a>Workspace

The working area (files and directories) that an agent can access within a sandbox. The workspace contains a clone of the managed repository on the assigned branch.

**Implementation Notes:**
- **Workspace Directory:** The path inside the pod (`/home/dev/workspace`)
- **Workspace Storage:** The persistent volume (PVC) that backs the workspace
- **Branch Workspace:** The dispatcher's per-branch directory (`/workspaces/{branch}`)

**Usage:** "The agent operates within the workspace", "Files in the workspace persist across sessions"

**Related:** [Sandbox](#sandbox), [Agent](#agent), [Managed Repository](#managed-repository)

---

## Infrastructure Components

### <a name="vm"></a>VM

The Vagrant-managed virtual machine that hosts the Kubernetes cluster and all yolo-cage services. Provisioned using either libvirt (Linux) or QEMU (macOS).

**Usage:** "Start the VM", "The VM is not running", "Destroy the VM"

**Related:** [Runtime](#runtime)

---

### <a name="dispatcher"></a>Dispatcher

The FastAPI service that enforces branch isolation and git policy. The dispatcher:
- Intercepts all git and GitHub CLI commands from agents
- Maintains a registry mapping pod IPs to assigned branches
- Enforces branch isolation on push operations
- Runs pre-push hooks (TruffleHog) to scan for secrets
- Executes git operations with authenticated credentials
- Never exposes GitHub credentials to agents

**Technical Details:** Listens on port 8080 within the Kubernetes cluster, communicates with agents via git-shim and gh-shim.

**Usage:** "The dispatcher enforces branch isolation", "The dispatcher runs pre-push hooks"

**Related:** [Branch Isolation](#branch-isolation), [Pre-Push Hooks](#pre-push-hooks), [Agent](#agent)

---

### <a name="egress-proxy"></a>Egress Proxy

The mitmproxy-based service that filters all agent HTTP/HTTPS traffic. The egress proxy:
- Scans request bodies, headers, and URLs for secrets using LLM-Guard
- Blocks requests to pastebin sites and file transfer services
- Blocks dangerous GitHub API operations (PR merge, repo delete)
- Allows bypass for configured domains
- Fails closed (blocks requests) if the secret scanner is unavailable

**Technical Details:** Operates as an HTTP/HTTPS proxy, agents are configured to route all traffic through it.

**Usage:** "The egress proxy filters network traffic", "Secrets detected by the egress proxy"

**Related:** [Agent](#agent), [Secret Scanning](#secret-scanning)

---

### <a name="pod"></a>Pod

The Kubernetes resource that hosts a sandbox. A pod is the implementation detail of how a sandbox runs.

**Domain vs Implementation:** Users interact with "sandboxes" (domain concept), while the implementation uses Kubernetes "pods". Code and documentation should prefer "sandbox" in user-facing contexts and "pod" only in infrastructure/implementation contexts.

**Usage:** In user-facing docs: "Create a sandbox". In infrastructure docs: "The pod is provisioned in the yolo-cage namespace"

**Related:** [Sandbox](#sandbox)

---

## Security Concepts

### <a name="branch-isolation"></a>Branch Isolation

The security property that ensures an agent can only push commits to its assigned branch. Branch isolation is enforced by:
1. The dispatcher verifying the current branch matches the assigned branch
2. The dispatcher rejecting refspec pushes to other branches
3. The dispatcher blocking push operations to arbitrary git URLs
4. The dispatcher blocking branch deletion

**Usage:** "The dispatcher enforces branch isolation", "Branch isolation prevents cross-contamination"

**Related:** [Dispatcher](#dispatcher), [Assigned Branch](#assigned-branch)

---

### <a name="secret-scanning"></a>Secret Scanning

The process of detecting and blocking sensitive information (API keys, tokens, credentials) from leaving the sandbox. Secret scanning occurs at two layers:

1. **Pre-push hooks:** TruffleHog scans commits before they reach GitHub
2. **Egress proxy:** LLM-Guard scans all HTTP/HTTPS request bodies, headers, and URLs

**Fail-Closed:** If secret scanning is unavailable, requests are blocked rather than allowed.

**Usage:** "Secret scanning detected a GitHub token", "Pre-push secret scanning failed"

**Related:** [Pre-Push Hooks](#pre-push-hooks), [Egress Proxy](#egress-proxy)

---

### <a name="pre-push-hooks"></a>Pre-Push Hooks

Git hooks that run before a push operation is allowed. The default hook uses TruffleHog to scan the last 10 commits for secrets.

**Execution:** The dispatcher runs pre-push hooks after validating branch isolation but before executing the push.

**Blocking:** If any hook fails (non-zero exit code), the push is rejected and the agent receives an error message.

**Usage:** "Pre-push hooks detected secrets in commit abc123", "Configure custom pre-push hooks"

**Related:** [Dispatcher](#dispatcher), [Secret Scanning](#secret-scanning)

---

## Configuration & Credentials

### <a name="configuration"></a>Configuration

User-provided settings and credentials stored in `~/.yolo-cage/config.env`. Configuration includes:

**Required:**
- `GITHUB_PAT`: GitHub Personal Access Token with push access to the managed repository
- `REPO_URL`: URL of the managed repository

**Optional:**
- `GIT_NAME`: Git commit author name (default: "yolo-cage")
- `GIT_EMAIL`: Git commit author email (default: "yolo-cage@localhost")
- `CLAUDE_OAUTH`: Claude OAuth token for authentication
- `PROXY_BYPASS`: Comma-separated list of domains that bypass the egress proxy

**Usage:** "Apply configuration to the runtime", "Validate configuration before creating a sandbox"

**Related:** [Runtime](#runtime), [Managed Repository](#managed-repository)

---

### <a name="github-pat"></a>GitHub PAT

GitHub Personal Access Token used by the dispatcher to authenticate git operations. The PAT:
- Must have push access to the managed repository
- Is validated during configuration
- Is stored in the dispatcher's environment
- Is **never exposed to agents**
- Is injected into git commands via `GIT_ASKPASS`

**Usage:** "Provide a GitHub PAT with repo scope", "The dispatcher uses the GitHub PAT for authenticated pushes"

**Related:** [Configuration](#configuration), [Dispatcher](#dispatcher)

---

## Operations

### <a name="attach"></a>Attach

The operation of connecting to an agent's interactive session within a sandbox. Attaching:
- Opens a tmux session running Claude Code in YOLO mode
- Provides the user with an interactive terminal to the agent
- Allows the user to observe and interact with the agent's work

**Technical Details:** Uses `kubectl exec` to attach to the pod's tmux session.

**Usage:** "Attach to a sandbox to interact with the agent", "Detach with Ctrl+B, D"

**Related:** [Sandbox](#sandbox), [Agent](#agent)

---

### <a name="bootstrap"></a>Bootstrap

The process of initializing a sandbox's workspace on first creation or when re-syncing. Bootstrapping:
- Detects the workspace state (empty, has .git, has files)
- Clones the managed repository if the workspace is empty
- Fetches and checks out the assigned branch if .git exists
- Fails if the workspace is in an inconsistent state

**Usage:** "Bootstrap the workspace on pod creation", "Workspace bootstrap failed"

**Related:** [Workspace](#workspace), [Sandbox](#sandbox), [Managed Repository](#managed-repository)

---

## Related Terms

### <a name="yolo-mode"></a>YOLO Mode

Claude Code's `--dangerously-skip-permissions` mode, which disables permission prompts for dangerous operations. yolo-cage uses YOLO mode because safety is enforced by the infrastructure (dispatcher, proxy, network policies) rather than user prompts.

**Usage:** "Agents run in YOLO mode within sandboxes"

**Related:** [Agent](#agent), [Sandbox](#sandbox)

---

### <a name="namespace"></a>Namespace

The Kubernetes namespace (`yolo-cage`) where all pods and services are deployed.

**Usage:** Infrastructure/implementation contexts only. Not typically user-facing.

**Related:** [Runtime](#runtime), [Pod](#pod)

---

## Quick Reference

| When you mean... | Use this term | Not this |
|------------------|---------------|----------|
| The whole infrastructure | Runtime | "VM", "platform", "environment" |
| The isolated environment for a branch | Sandbox | "pod", "container" |
| The AI working in a sandbox | Agent | "Claude", "bot", "the AI" |
| The user's project repository | Managed Repository | "the repo", "repository" |
| yolo-cage's own codebase | System Repository | "the repo", "yolo-cage repo" |
| The branch a sandbox works on | Assigned Branch | "target branch", "bound branch" |
| The files an agent can access | Workspace | "working directory", "repo clone" |
| The service that enforces git policy | Dispatcher | "git proxy", "git server" |
| The service that filters traffic | Egress Proxy | "HTTP proxy", "MITM proxy" |
| Connecting to an agent session | Attach | "connect", "SSH", "enter" |

---

## Updates to This Glossary

This glossary is a living document. When introducing new concepts or refining existing ones, update this file first, then update code and documentation to match.

All terms should be linked from documentation using markdown anchors: `[sandbox](glossary.md#sandbox)`
