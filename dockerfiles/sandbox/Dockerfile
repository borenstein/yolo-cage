# yolo-cage v2 - Claude Code sandbox with git dispatcher
# Full-stack development environment with enforced branch isolation

FROM python:3.12-slim-bookworm

# Install system dependencies
# Note: git is installed but will be shadowed by our shim
# Note: openssh-client kept for compatibility but blocked by NetworkPolicy
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    jq \
    make \
    tmux \
    openssh-client \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js LTS (22.x)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user for development
RUN useradd -m -s /bin/bash dev \
    && mkdir -p /workspace \
    && chown -R dev:dev /workspace

# Install uv for dev user as well
USER dev
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/dev/.local/bin:$PATH"

# Working directory
WORKDIR /workspace

# Copy scripts
COPY scripts/git-shim /usr/local/bin/git-shim
COPY scripts/yolo-cage-init /usr/local/bin/yolo-cage-init
USER root
RUN chmod +x /usr/local/bin/git-shim /usr/local/bin/yolo-cage-init

# Create a wrapper that uses the git shim
# Real git is at /usr/bin/git, shim intercepts at /usr/local/bin/git
RUN echo '#!/bin/bash' > /usr/local/bin/git && \
    echo 'exec /usr/local/bin/git-shim "$@"' >> /usr/local/bin/git && \
    chmod +x /usr/local/bin/git

USER dev

# Environment for git dispatcher (overridden by pod env)
ENV YOLO_CAGE_DISPATCHER="http://git-dispatcher:8080"

# Default command - run init script then sleep
CMD ["/usr/local/bin/yolo-cage-init"]
