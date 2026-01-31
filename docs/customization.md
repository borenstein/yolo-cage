# Customization Guide

This guide covers advanced customizations beyond the standard [Configuration Reference](configuration.md). For terminology, see the [glossary](glossary.md).

> **Note**: When customizing, maintain the security properties: non-root user, NetworkPolicy egress restrictions, and proxy-based scanning. Disabling these removes exfiltration controls.

## Modifying Manifests

For advanced configuration, SSH into the VM and edit manifests directly:

```bash
vagrant ssh
cd /home/vagrant/yolo-cage/manifests
# Edit files as needed
kubectl apply -f <file.yaml> -n yolo-cage
```

After modifying deployments, restart them to pick up changes:

```bash
kubectl rollout restart deployment/git-dispatcher -n yolo-cage
kubectl rollout restart deployment/egress-proxy -n yolo-cage
```

## Adding Languages and Tools

### Modifying the Sandbox Image

Edit `dockerfiles/sandbox/Dockerfile` to add your stack:

```dockerfile
# Example: Add Go
RUN curl -LO https://go.dev/dl/go1.22.0.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go1.22.0.linux-amd64.tar.gz \
    && rm go1.22.0.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:$PATH"

# Example: Add Rust
USER root
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"
USER dev
```

Then rebuild inside the VM:

```bash
vagrant ssh
cd /home/vagrant/yolo-cage
docker build -t localhost:32000/yolo-cage:latest -f dockerfiles/sandbox/Dockerfile .
docker push localhost:32000/yolo-cage:latest
```

New [sandboxes](glossary.md#sandbox) will use the updated image. Existing sandboxes need to be deleted and recreated.

## Adding Secret Patterns

### LLM-Guard Configuration

Edit `manifests/proxy/llm-guard.yaml` to add custom patterns to the args section:

```yaml
args:
  - "--config"
  - |
    input_scanners:
      - type: Secrets
        params:
          redact_mode: "all"
      - type: Regex
        params:
          patterns:
            # Default patterns
            - "-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"
            - "AKIA[0-9A-Z]{16}"
            - "sk-ant-[a-zA-Z0-9-_]+"
            - "ghp_[a-zA-Z0-9]{36}"
            # Add your custom patterns here
            - "mycompany_api_[a-f0-9]{40}"
```

After editing, apply and restart:

```bash
kubectl apply -f manifests/proxy/llm-guard.yaml -n yolo-cage
kubectl rollout restart deployment/llm-guard -n yolo-cage
```

## Modifying Blocked Domains

Edit `manifests/proxy/configmap.yaml`:

```yaml
data:
  BLOCKED_DOMAINS: |
    [
      "pastebin.com",
      "paste.ee",
      "your-blocked-site.com"
    ]
```

Apply and restart the proxy:

```bash
kubectl apply -f manifests/proxy/configmap.yaml -n yolo-cage
kubectl rollout restart deployment/egress-proxy -n yolo-cage
```

## Modifying GitHub API Restrictions

Edit `manifests/proxy/configmap.yaml`:

```yaml
data:
  GITHUB_API_BLOCKED: |
    [
      ["PUT", "/repos/[^/]+/[^/]+/pulls/\\d+/merge"],
      ["DELETE", "/repos/.*"],
      ["YOUR_METHOD", "your-pattern-here"]
    ]
```

## Custom Init Scripts

Run project-specific setup when pods start. Edit `manifests/sandbox/configmap.yaml`:

```yaml
data:
  init-workspace: |
    #!/bin/bash
    cd /home/dev/workspace
    pip install -r requirements.txt
    npm install
```

The script runs after the workspace is cloned but before the agent starts.

## Resource Limits

### Per-Pod Resources

Set in your `~/.yolo-cage/config.env`:

```bash
POD_MEMORY_LIMIT=8Gi
POD_MEMORY_REQUEST=2Gi
POD_CPU_LIMIT=4
POD_CPU_REQUEST=1
```

Run `yolo-cage-configure` inside the VM to apply.

### Dispatcher and Proxy Resources

Edit the respective deployment files in `manifests/dispatcher/deployment.yaml` and `manifests/proxy/egress-proxy.yaml`:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "1Gi"
    cpu: "1"
```

## VM Resources

Edit the `Vagrantfile` before building:

```ruby
config.vm.provider "libvirt" do |lv|
  lv.memory = 16384  # 16GB
  lv.cpus = 8
end
```

Then rebuild:

```bash
yolo-cage build
```

## Multiple Repositories

To work with multiple repositories, create separate config files and rebuild:

```bash
# Project A
cp ~/.yolo-cage/config.env ~/.yolo-cage/project-a.env
# Edit project-a.env with REPO_URL for project A

yolo-cage destroy
yolo-cage build --config-file ~/.yolo-cage/project-a.env --up
```

Each yolo-cage instance works with one repository at a time.

## Restricting GitHub CLI Access

The dispatcher blocks dangerous `gh` commands (merge, delete, api, etc.), but you can add defense-in-depth by using fine-grained PATs:

1. Go to [GitHub Settings > Developer settings > Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. Create a token with only the permissions you need
3. Use this token in your `config.env`

With an issues-only token, commands like `gh pr merge` would fail at GitHub's API level even if they bypassed the dispatcher.

## Observability

### Viewing Logs

```bash
vagrant ssh

# Dispatcher logs
kubectl logs -n yolo-cage deployment/git-dispatcher -f

# Proxy logs
kubectl logs -n yolo-cage deployment/egress-proxy -f

# Pod logs
kubectl logs -n yolo-cage yolo-cage-<branch> -f
```

### Proxy Traffic Log

The egress proxy logs all requests to `/var/log/proxy/requests.jsonl` inside its container:

```bash
kubectl exec -n yolo-cage deployment/egress-proxy -- tail -f /var/log/proxy/requests.jsonl
```

## Disabling Components (Not Recommended)

### Run Without Secret Scanning

To disable the proxy entirely, remove the proxy environment variables from `manifests/sandbox/pod-template.yaml`:

```yaml
# Remove these lines:
- name: HTTP_PROXY
  value: "http://egress-proxy:8080"
- name: HTTPS_PROXY
  value: "http://egress-proxy:8080"
```

This removes exfiltration protection entirely.

### Run Without Pre-Push Hooks

Edit `manifests/dispatcher/configmap.yaml`:

```yaml
data:
  PRE_PUSH_HOOKS: '[]'
```

This allows pushing commits containing secrets.
