# Yolo-cage - Claude Code sandbox for YOLO mode development
# Full-stack development environment with Claude Code CLI

FROM python:3.12-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
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

# Set up SSH directory
RUN mkdir -p /home/dev/.ssh && chmod 700 /home/dev/.ssh

# Working directory
WORKDIR /workspace

# Copy helper scripts
COPY scripts/ /home/dev/bin/
USER root
RUN chown -R dev:dev /home/dev/bin && chmod +x /home/dev/bin/*
USER dev
ENV PATH="/home/dev/bin:$PATH"

# Default command - keep container running
CMD ["sleep", "infinity"]
