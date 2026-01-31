# Domain Model Analysis - yolo-cage Refactoring

**Date:** 2026-01-31
**Purpose:** Document the domain responsibilities across the VM boundary to guide the refactoring from bash (yolo-cage-inner) to Python

---

## HOST SIDE - Responsibilities

### Runtime Lifecycle

**Building the runtime:**
- The host validates that prerequisites are installed (vagrant, git, qemu/libvirt)
- The host ensures configuration exists (either from file, interactive prompt, or existing)
- The host validates the configuration by checking GitHub repository access with the provided PAT
- The host clones the system repository if not running in development mode
- The host provisions the VM using Vagrant
- The host syncs configuration to the VM
- The host instructs the VM to apply the configuration to Kubernetes
- Optionally, the host keeps the VM running or halts it

**Starting the runtime:**
- The host ensures the system repository exists
- The host brings up the VM using Vagrant
- The VM is now ready to accept sandbox operations

**Stopping the runtime:**
- The host halts the VM using Vagrant
- All sandboxes remain intact (persistent storage)

**Destroying the runtime:**
- The host confirms the destructive operation with the user
- The host destroys the VM using Vagrant
- The host preserves configuration (in ~/.yolo-cage/config.env)

**Upgrading the runtime:**
- The host downloads the latest CLI binary
- The host updates the system repository
- Optionally, the host rebuilds the VM with updated infrastructure

### Configuration Management

**Prompting for configuration:**
- The host interactively prompts for: GitHub PAT, repository URL, git identity, optional Claude OAuth, optional proxy bypass
- The host validates GitHub repository access before accepting the configuration
- The host writes configuration to ~/.yolo-cage/config.env

**Loading configuration:**
- The host reads configuration from ~/.yolo-cage/config.env
- The host parses key=value pairs, ignoring comments and blank lines

**Syncing configuration to VM:**
- The host ensures the VM is accessible
- The host creates the .yolo-cage directory in the VM
- The host copies configuration content to the VM's ~/.yolo-cage/config.env
- The host instructs the VM to apply the configuration

**Validating configuration:**
- The host extracts owner/repo from the GitHub URL (supports HTTPS and SSH formats)
- The host calls the GitHub API to verify repository existence
- The host verifies the PAT has push permissions
- The host reports success or specific failure (404, 401, 403, network error)

### Repository Management

**Detecting the system repository:**
- The host checks if running from within a development clone (../Vagrantfile exists)
- The host checks if ~/.yolo-cage/repo exists (installed mode)
- The host returns the repository location or None

**Ensuring the system repository exists:**
- The host detects the repository location
- If not found, the host exits with an error instructing the user to run 'build'

### VM Interaction

**Determining Vagrant provider:**
- On macOS, the host specifies --provider=qemu
- On Linux, the host uses the default provider (libvirt or virtualbox)

**Checking VM status:**
- The host runs 'vagrant status --machine-readable'
- The host parses the output to extract the VM state (running, stopped, not created)

**Ensuring VM is running:**
- The host checks VM status
- If not running, the host exits with an error instructing the user to run 'up'

**Executing commands in the VM:**
- For non-interactive commands: the host uses 'vagrant ssh -c "command"'
- For interactive commands: the host uses 'vagrant ssh -- -t "command"' (allocates TTY)
- The host propagates the exit code and output

### Sandbox Operation Delegation

**All sandbox operations are delegated to the VM:**
- Creating a sandbox → host validates repo access, then instructs VM to create
- Listing sandboxes → host instructs VM to list
- Attaching to a sandbox → host instructs VM to attach (interactive)
- Opening a shell in a sandbox → host instructs VM to shell (interactive)
- Deleting a sandbox → host instructs VM to delete
- Viewing logs → host instructs VM to show logs
- Port forwarding → host establishes SSH tunnel and instructs VM to forward port

**KEY INSIGHT:** The host NEVER directly interacts with sandboxes, Kubernetes, or the dispatcher. All sandbox operations are delegated to the VM side.

### Status Reporting

**Showing overall status:**
- The host reports the system repository location
- The host reports the configuration file location
- The host checks and reports VM status
- If the VM is running, the host delegates to VM to list sandboxes

---

## VM SIDE - Responsibilities

### Configuration Application

**Applying configuration:**
- The VM reads configuration from ~/.yolo-cage/config.env
- The VM creates/updates Kubernetes secrets with: GITHUB_PAT, CLAUDE_OAUTH
- The VM creates/updates Kubernetes configmaps with: GIT_NAME, GIT_EMAIL, REPO_URL, PROXY_BYPASS
- The VM restarts the dispatcher to pick up new configuration

### Sandbox Lifecycle

**Creating a sandbox:**
- The VM receives a branch name
- The VM transforms the branch name to a pod name (lowercase, replace /_ with -)
- The VM discovers the dispatcher URL by querying the git-dispatcher service's ClusterIP
- The VM calls the dispatcher: POST /pods with {"branch": "{branch}"}
- The dispatcher creates the pod, bootstraps the workspace, and registers it
- The dispatcher returns a response with status (e.g., "Pending")
- The VM waits for the pod to become Ready via kubectl wait
- The VM reports success and instructs the user how to attach

**Listing sandboxes:**
- The VM discovers the dispatcher URL
- The VM calls the dispatcher: GET /pods
- The dispatcher returns JSON: {pods: [{branch: "x", status: "Running"}, ...]}
- The VM formats and displays the list as a table

**Attaching to a sandbox:**
- The VM receives a branch name
- The VM transforms the branch name to a pod name
- The VM executes kubectl exec to attach to the pod
- The VM starts a tmux session named "claude" running Claude Code in YOLO mode
- The user is now interacting with the agent

**Opening a shell in a sandbox:**
- The VM receives a branch name
- The VM transforms the branch name to a pod name
- The VM executes kubectl exec to attach to the pod
- The VM starts a tmux session named "shell" running bash
- The user has direct bash access

**Deleting a sandbox:**
- The VM receives a branch name and optional --clean flag
- The VM discovers the dispatcher URL
- The VM calls the dispatcher: DELETE /pods/{branch}?clean=true (if --clean specified)
- The dispatcher deletes the pod and optionally cleans workspace storage
- The VM displays the response status

**Viewing logs:**
- The VM receives a branch name
- The VM transforms the branch name to a pod name
- The VM executes kubectl logs -f to tail the pod's logs
- The user sees the pod's stdout/stderr

### Dispatcher URL Discovery

**Finding the dispatcher:**
- The VM queries Kubernetes: kubectl get svc -n yolo-cage git-dispatcher -o jsonpath='{.spec.clusterIP}'
- The VM constructs the URL: http://{ClusterIP}:8080
- The ClusterIP is directly reachable from the VM (single-node MicroK8s)

---

## DISPATCHER SIDE - Responsibilities

### Sandbox Lifecycle Management

**Creating a sandbox (POST /pods):**
- The dispatcher receives a branch name
- The dispatcher checks if a pod already exists for that branch
- The dispatcher renders a pod manifest from the template, substituting the branch name
- The dispatcher creates the pod via Kubernetes API
- The dispatcher waits for the pod to become Ready
- The dispatcher returns the pod status (Pending, Running, etc.)

**Listing sandboxes (GET /pods):**
- The dispatcher queries Kubernetes for all pods in the yolo-cage namespace
- The dispatcher extracts branch names from pod names
- The dispatcher returns JSON with branch names and statuses

**Deleting a sandbox (DELETE /pods/{branch}):**
- The dispatcher receives a branch name and optional clean flag
- The dispatcher deletes the pod via Kubernetes API
- If clean flag is set, the dispatcher also deletes workspace files from the PVC
- The dispatcher returns success status

### Workspace Management

**Bootstrapping a workspace (POST /bootstrap):**
- The dispatcher receives a branch name (called by pod init script)
- The dispatcher detects the workspace state (empty, has .git, has files but no .git)
- If empty: the dispatcher clones the managed repository
- If has .git: the dispatcher fetches and checks out the assigned branch
- If has files but no .git: the dispatcher returns an error (corrupted state)
- The dispatcher returns success or failure

**Cleaning a workspace:**
- The dispatcher receives a branch name (called during DELETE with clean flag)
- The dispatcher removes the workspace directory from /workspaces/{branch}
- The dispatcher returns success

### Pod Registry Management

**Registering a pod (POST /register):**
- The dispatcher receives a branch name and extracts the pod's IP address from the HTTP request
- The dispatcher stores the mapping: pod IP → branch name in memory
- The dispatcher returns success

**Looking up a pod's assigned branch:**
- The dispatcher receives an HTTP request (from git-shim or gh-shim)
- The dispatcher extracts the source IP address
- The dispatcher looks up the assigned branch from the IP → branch registry
- If not found, the dispatcher returns 403 Forbidden

### Git Command Enforcement

**Handling git commands (POST /git):**
- The dispatcher receives: {args: ["push", "origin", "branch"], cwd: "/home/dev/workspace"}
- The dispatcher extracts the pod IP from the request
- The dispatcher looks up the assigned branch
- The dispatcher translates the workspace path from pod view to dispatcher view
- The dispatcher classifies the command (LOCAL, BRANCH, MERGE, REMOTE_READ, REMOTE_WRITE, DENIED)
- Based on classification, enforces appropriate policy
- For REMOTE_WRITE (push): verifies branch isolation, runs pre-push hooks, executes with auth
- The dispatcher returns stdout, stderr, and exit code

### GitHub CLI Command Enforcement

**Handling gh commands (POST /gh):**
- The dispatcher receives: {args: ["pr", "create", ...], cwd: "/home/dev/workspace"}
- The dispatcher classifies the command using allowlists
- Blocked commands: pr merge, repo delete, auth login, secret, api, etc.
- Allowed commands: issue create/view, pr create/view/comment, repo view, etc.
- The dispatcher executes allowed commands with GitHub authentication
- The dispatcher returns stdout, stderr, and exit code

---

## POD SIDE - Responsibilities

### Initialization

**Pod startup (yolo-cage-init):**
- The pod waits for the dispatcher to be healthy (HTTP health check)
- The pod calls the dispatcher: POST /bootstrap?branch={branch}
- The dispatcher clones/syncs the managed repository
- The pod calls the dispatcher: POST /register?branch={branch}
- The dispatcher records the pod IP → branch mapping
- The pod runs the user's custom init script (if configured)
- The pod enters sleep infinity (keeping the container alive for tmux sessions)

### Command Interception

**Git command interception (git-shim):**
- The agent executes: git push origin feature-branch
- The git-shim intercepts (installed at /usr/local/bin/git)
- The git-shim serializes: {args: ["push", "origin", "feature-branch"], cwd: "/home/dev/workspace"}
- The git-shim POSTs to: http://git-dispatcher:8080/git
- The git-shim extracts the exit code from response header X-Yolo-Cage-Exit-Code
- The git-shim returns stdout/stderr and exit code to the agent

---

## INTERACTION BOUNDARIES

### Host → VM Communication

**Transport:** Vagrant SSH
- Non-interactive: `vagrant ssh -c "yolo-cage-inner create feature-x"`
- Interactive: `vagrant ssh -- -t "yolo-cage-inner attach feature-x"`

### VM → Dispatcher Communication

**Transport:** HTTP REST API over ClusterIP

**Discovery:**
```bash
kubectl get svc -n yolo-cage git-dispatcher -o jsonpath='{.spec.clusterIP}'
# Returns: 10.152.183.X (ClusterIP)
# Construct: http://10.152.183.X:8080
```

**Endpoints:**
- `POST /pods` - Create sandbox
- `GET /pods` - List sandboxes
- `DELETE /pods/{branch}?clean=true` - Delete sandbox

### VM → Kubernetes Communication

**Transport:** kubectl CLI

**Operations:**
- `kubectl wait --for=condition=Ready pod/{name}` - Wait for pod readiness
- `kubectl exec -it pod/{name} -- bash` - Interactive shell/attach
- `kubectl logs -f pod/{name}` - Tail logs
- `kubectl get svc` - Service discovery

---

## RESPONSIBILITY MATRIX

| Responsibility | Host | VM | Dispatcher | Pod |
|----------------|------|-----|------------|-----|
| Runtime lifecycle | ✓ | | | |
| Configuration validation | ✓ | | | |
| Configuration sync to VM | ✓ | | | |
| Configuration application to K8s | | ✓ | | |
| Sandbox creation orchestration | | ✓ | ✓ | |
| Sandbox deletion orchestration | | ✓ | ✓ | |
| Sandbox listing | | ✓ | ✓ | |
| Sandbox attachment | | ✓ | | |
| Dispatcher URL discovery | | ✓ | | |
| Workspace bootstrap | | | ✓ | |
| Pod registration | | | ✓ | ✓ |
| Branch isolation enforcement | | | ✓ | |
| Git command execution | | | ✓ | |
| Pre-push hooks | | | ✓ | |
| GitHub authentication | | | ✓ | |
| Git command interception | | | | ✓ |
| Agent execution | | | | ✓ |

---

## PROPOSED PYTHON STRUCTURE

```python
yolo_cage/
  __init__.py
  main.py                    # Entry point (context detection)

  domain/
    __init__.py
    branch.py                # Branch value object
    sandbox.py               # Sandbox entity
    config.py                # Config value object

  host/
    __init__.py
    runtime.py               # Build, up, down, destroy, upgrade
    config_mgmt.py           # Configure, validate, sync
    vagrant.py               # Vagrant abstraction
    commands.py              # Command handlers (cmd_build, etc.)

  vm/
    __init__.py
    sandbox_ops.py           # Create, delete, attach, shell, list, logs
    kubernetes.py            # kubectl abstraction
    dispatcher_client.py     # HTTP client for dispatcher API
    config_apply.py          # Apply config to K8s
    commands.py              # Command handlers (cmd_create, etc.)

  common/
    __init__.py
    logging.py               # log_step, log_error, log_success
    validation.py            # Validators
    errors.py                # Custom exceptions
    github.py                # GitHub API utilities
```

---

## MIGRATION STRATEGY

### Phase 1: Create shared domain model and utilities
- Domain value objects: Branch, Config
- Common utilities: logging, validation
- Keep existing scripts working

### Phase 2: Refactor VM side to Python
- Implement vm/ module with same functionality as yolo-cage-inner
- Create new entry point: yolo-cage-vm (or detect context)
- Test against existing host CLI

### Phase 3: Unify entry points
- Single entry point that detects host vs VM context
- Host side calls Python VM side instead of bash
- Remove yolo-cage-inner bash script

### Phase 4: Clean up and polish
- Update documentation
- Add comprehensive tests
- Ensure consistent error handling and logging

---

## NEXT STEPS

1. Create the directory structure
2. Implement domain model (Branch, Sandbox, Config)
3. Implement common utilities
4. Implement VM operations in Python
5. Test alongside existing bash script
6. Switch host to call Python VM operations
7. Remove bash script
8. Update documentation
