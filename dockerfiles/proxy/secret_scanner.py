"""
mitmproxy addon that scans request bodies for secrets using LLM-Guard.
Blocks requests containing detected secrets and logs all traffic.

DISCLAIMER: This provides defense-in-depth, not absolute security.
Sophisticated attacks (DNS exfiltration, steganography, URL path encoding)
may bypass this scanner. Use scoped credentials and do not rely on this
as your only security control. See LICENSE for warranty disclaimers.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

import requests
from mitmproxy import http, ctx

# Configuration
LLM_GUARD_URL = os.environ.get("LLM_GUARD_URL", "http://llm-guard:8000")
LLM_GUARD_TOKEN = os.environ.get("LLM_GUARD_TOKEN", "internal-only")
LOG_FILE = os.environ.get("LOG_FILE", "/var/log/proxy/requests.jsonl")

# Blocklist for known exfiltration sites
BLOCKED_DOMAINS = {
    "pastebin.com",
    "paste.ee",
    "hastebin.com",
    "dpaste.org",
    "file.io",
    "transfer.sh",
    "0x0.st",
    "ix.io",
    "sprunge.us",
    "termbin.com",
}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("secret_scanner")


class SecretScanner:
    def __init__(self):
        self.llm_guard_available = False
        self._check_llm_guard()

    def _check_llm_guard(self):
        """Check if LLM-Guard is available."""
        try:
            resp = requests.get(f"{LLM_GUARD_URL}/healthz", timeout=5)
            self.llm_guard_available = resp.status_code == 200
            if self.llm_guard_available:
                logger.info("LLM-Guard is available")
            else:
                logger.warning(f"LLM-Guard returned status {resp.status_code}")
        except Exception as e:
            logger.warning(f"LLM-Guard not available: {e}")
            self.llm_guard_available = False

    def _scan_for_secrets(self, text: str) -> tuple[bool, list[str]]:
        """
        Scan text for secrets using LLM-Guard.
        Returns (has_secrets, list of detected types).
        """
        if not text or len(text) < 10:
            return False, []

        if not self.llm_guard_available:
            self._check_llm_guard()
            if not self.llm_guard_available:
                # Fail open if LLM-Guard is down (log warning)
                logger.warning("LLM-Guard unavailable, allowing request")
                return False, []

        try:
            resp = requests.post(
                f"{LLM_GUARD_URL}/analyze/prompt",
                json={"prompt": text},
                headers={"Authorization": f"Bearer {LLM_GUARD_TOKEN}"},
                timeout=10,
            )
            if resp.status_code == 200:
                result = resp.json()
                logger.debug(f"LLM-Guard response: {result}")

                # Top-level is_valid indicates if content passed all scanners
                is_valid = result.get("is_valid", True)
                if not is_valid:
                    # Find which scanners flagged (score < 1.0 means flagged)
                    scanners = result.get("scanners", {})
                    detected = [name for name, score in scanners.items() if score < 1.0]
                    logger.info(f"Secrets detected by scanners: {detected}")
                    return True, detected
                return False, []
            else:
                logger.warning(f"LLM-Guard returned status {resp.status_code}")
        except Exception as e:
            logger.error(f"Error calling LLM-Guard: {e}")

        return False, []

    def _log_request(
        self,
        flow: http.HTTPFlow,
        blocked: bool,
        reason: Optional[str] = None,
        detected_secrets: Optional[list] = None,
    ):
        """Log request details to JSONL file."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "host": flow.request.host,
            "blocked": blocked,
            "reason": reason,
            "detected_secrets": detected_secrets,
            "request_size": len(flow.request.content) if flow.request.content else 0,
        }

        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write log: {e}")

        # Also log to stdout for kubectl logs
        if blocked:
            logger.warning(f"BLOCKED: {flow.request.method} {flow.request.pretty_url} - {reason}")
        else:
            logger.info(f"ALLOWED: {flow.request.method} {flow.request.pretty_url}")

    def request(self, flow: http.HTTPFlow):
        """Intercept and scan outgoing requests."""
        host = flow.request.host

        # Check domain blocklist
        for blocked_domain in BLOCKED_DOMAINS:
            if host == blocked_domain or host.endswith(f".{blocked_domain}"):
                flow.response = http.Response.make(
                    403,
                    b"Blocked: destination is on blocklist",
                    {"Content-Type": "text/plain"},
                )
                self._log_request(flow, blocked=True, reason=f"blocked_domain:{blocked_domain}")
                return

        # Scan request body for secrets
        body = flow.request.get_text()
        if body:
            has_secrets, detected = self._scan_for_secrets(body)
            if has_secrets:
                flow.response = http.Response.make(
                    403,
                    b"Blocked: request body contains potential secrets",
                    {"Content-Type": "text/plain"},
                )
                self._log_request(
                    flow,
                    blocked=True,
                    reason="secrets_detected",
                    detected_secrets=detected,
                )
                return

        # Also scan URL parameters (secrets sometimes end up in URLs)
        url = flow.request.pretty_url
        if len(url) > 100:  # Only scan long URLs
            has_secrets, detected = self._scan_for_secrets(url)
            if has_secrets:
                flow.response = http.Response.make(
                    403,
                    b"Blocked: URL contains potential secrets",
                    {"Content-Type": "text/plain"},
                )
                self._log_request(
                    flow,
                    blocked=True,
                    reason="secrets_in_url",
                    detected_secrets=detected,
                )
                return

        self._log_request(flow, blocked=False)


addons = [SecretScanner()]
