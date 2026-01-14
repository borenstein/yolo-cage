"""Configuration loading for the git dispatcher."""

import json
import os


WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/workspaces")
REPO_URL = os.environ.get("REPO_URL", "")
GIT_USER_NAME = os.environ.get("GIT_USER_NAME", "yolo-cage")
GIT_USER_EMAIL = os.environ.get("GIT_USER_EMAIL", "yolo-cage@localhost")
GITHUB_PAT = os.environ.get("GITHUB_PAT", "")
YOLO_CAGE_VERSION = os.environ.get("YOLO_CAGE_VERSION", "0.2.0")

DEFAULT_PRE_PUSH_HOOKS = [
    # Use --max-depth instead of --since-commit to avoid issues with shallow repos
    "trufflehog git file://. --max-depth=10 --fail --no-update"
]
PRE_PUSH_HOOKS = json.loads(
    os.environ.get("PRE_PUSH_HOOKS", json.dumps(DEFAULT_PRE_PUSH_HOOKS))
)

COMMIT_FOOTER = os.environ.get(
    "COMMIT_FOOTER",
    f"Built autonomously using yolo-cage v{YOLO_CAGE_VERSION}"
)
