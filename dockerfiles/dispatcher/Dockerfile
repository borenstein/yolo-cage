# yolo-cage Git Dispatcher
# Executes git commands on behalf of sandboxed agents
# Includes TruffleHog for pre-push secret scanning

FROM python:3.12-slim

# Install git and curl (for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI (needed for /gh endpoint)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install TruffleHog from GitHub releases
ARG TRUFFLEHOG_VERSION=3.63.2
RUN curl -sSL https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_linux_amd64.tar.gz \
    | tar -xz -C /usr/local/bin trufflehog \
    && chmod +x /usr/local/bin/trufflehog

# Create non-root user
RUN useradd -m -s /bin/bash dispatcher
WORKDIR /app

# Install Python dependencies
COPY dispatcher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy dispatcher package
COPY dispatcher/ ./dispatcher/

# Copy pod template for /pods API
COPY manifests/sandbox/pod-template.yaml ./pod-template.yaml

# Create workspace mount point
RUN mkdir -p /workspaces && chown dispatcher:dispatcher /workspaces

USER dispatcher

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["uvicorn", "dispatcher.app:app", "--host", "0.0.0.0", "--port", "8080"]
