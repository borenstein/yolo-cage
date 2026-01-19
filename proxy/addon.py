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
from urllib.parse import unquote

import requests
from mitmproxy import http

from policy import check_blocked_domain, check_github_api

# Configuration
LLM_GUARD_URL = os.environ.get("LLM_GUARD_URL", "http://llm-guard:8000")
LLM_GUARD_TOKEN = os.environ.get("LLM_GUARD_TOKEN", "internal-only")
LOG_FILE = os.environ.get("LOG_FILE", "/var/log/proxy/requests.jsonl")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("egress_proxy")


class EgressProxy:
    """mitmproxy addon that enforces egress policy and scans for secrets."""

    def __init__(self):
        self.llm_guard_available = False
        self._check_llm_guard()

    def _check_llm_guard(self) -> None:
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
        Fails closed if scanner is unavailable.
        """
        if not text or len(text) < 10:
            return False, []

        if not self.llm_guard_available:
            self._check_llm_guard()
            if not self.llm_guard_available:
                logger.error("LLM-Guard unavailable, blocking request (fail-closed)")
                return True, ["scanner_unavailable"]

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

                is_valid = result.get("is_valid", True)
                if not is_valid:
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
    ) -> None:
        """Log request details to JSONL file and stdout."""
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

        if blocked:
            logger.warning(f"BLOCKED: {flow.request.method} {flow.request.pretty_url} - {reason}")
        else:
            logger.info(f"ALLOWED: {flow.request.method} {flow.request.pretty_url}")

    def _block(self, flow: http.HTTPFlow, message: bytes, reason: str, secrets: Optional[list] = None) -> None:
        """Block a request with a 403 response."""
        flow.response = http.Response.make(
            403,
            message,
            {"Content-Type": "text/plain"},
        )
        self._log_request(flow, blocked=True, reason=reason, detected_secrets=secrets)

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept and scan outgoing requests."""
        host = flow.request.host
        method = flow.request.method
        path = flow.request.path

        # Check GitHub API policy
        github_block = check_github_api(host, method, path)
        if github_block:
            self._block(flow, b"Blocked: this GitHub API operation is not permitted in yolo-cage", github_block)
            return

        # Check domain blocklist
        blocked_domain = check_blocked_domain(host)
        if blocked_domain:
            self._block(flow, b"Blocked: destination is on blocklist", f"blocked_domain:{blocked_domain}")
            return

        # Scan request body for secrets
        body = flow.request.get_text()
        if body:
            has_secrets, detected = self._scan_for_secrets(body)
            if has_secrets:
                self._block(flow, b"Blocked: request body contains potential secrets", "secrets_detected", detected)
                return

        # Scan URL query parameters for secrets
        query = flow.request.query
        if query:
            query_text = "&".join(f"{k}={v}" for k, v in query.items())
            has_secrets, detected = self._scan_for_secrets(query_text)
            if has_secrets:
                self._block(flow, b"Blocked: URL query parameters contain potential secrets", "secrets_in_query", detected)
                return

        # Scan URL path for secrets (decode URL encoding first)
        decoded_path = unquote(path)
        if len(decoded_path) > 10:  # Skip trivial paths
            has_secrets, detected = self._scan_for_secrets(decoded_path)
            if has_secrets:
                self._block(flow, b"Blocked: URL path contains potential secrets", "secrets_in_path", detected)
                return

        # Scan ALL headers for secrets (not just known auth headers)
        for header_name, header_value in flow.request.headers.items():
            if header_value and len(header_value) > 10:
                has_secrets, detected = self._scan_for_secrets(header_value)
                if has_secrets:
                    self._block(flow, b"Blocked: request header contains potential secrets",
                               f"secrets_in_header:{header_name}", detected)
                    return

        self._log_request(flow, blocked=False)


addons = [EgressProxy()]
