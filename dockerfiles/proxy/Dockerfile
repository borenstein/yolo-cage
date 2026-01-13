# Egress proxy with secret scanning
# Based on mitmproxy with custom addon

FROM mitmproxy/mitmproxy:latest

USER root

# Install requests for LLM-Guard API calls
RUN pip install --no-cache-dir requests

# Create log directory
RUN mkdir -p /var/log/proxy && chown mitmproxy:mitmproxy /var/log/proxy

# Copy proxy modules
COPY dockerfiles/proxy/policy.py /home/mitmproxy/policy.py
COPY dockerfiles/proxy/addon.py /home/mitmproxy/addon.py

USER mitmproxy

# Run mitmproxy with egress proxy addon
ENTRYPOINT ["mitmdump", "-s", "/home/mitmproxy/addon.py", "--set", "block_global=false", "--listen-host", "0.0.0.0", "--listen-port", "8080"]
