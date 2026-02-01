"""Configuration file handling."""

from pathlib import Path

from ..output import die, log_step, log_success
from .github import validate_repo_access


def load_config(path: Path) -> dict[str, str]:
    """Load config.env file as dictionary."""
    if not path.exists():
        return {}

    config = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def save_config(path: Path, pat: str, repo: str, name: str, email: str,
                claude_oauth: str = "", proxy_bypass: str = "") -> None:
    """Write config.env file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write("# yolo-cage configuration\n\n")
        f.write(f"GITHUB_PAT={pat}\n")
        f.write(f"REPO_URL={repo}\n")
        f.write(f"GIT_NAME={name}\n")
        f.write(f"GIT_EMAIL={email}\n")
        if claude_oauth:
            f.write(f"CLAUDE_OAUTH={claude_oauth}\n")
        if proxy_bypass:
            f.write(f"PROXY_BYPASS={proxy_bypass}\n")


def prompt_config(config_path: Path) -> None:
    """Interactively prompt for configuration."""
    print("yolo-cage configuration\n")

    pat = input("GitHub PAT: ").strip()
    if not pat:
        die("GitHub PAT is required")

    repo = input("Repository URL: ").strip()
    if not repo:
        die("Repository URL is required")

    log_step("Validating repository access...")
    valid, message = validate_repo_access(repo, pat)
    if not valid:
        die(message)
    log_success(message)

    name = input("Git name [yolo-cage]: ").strip() or "yolo-cage"
    email = input("Git email [yolo-cage@localhost]: ").strip() or "yolo-cage@localhost"
    claude_oauth = input("Claude OAuth token (optional): ").strip()
    proxy_bypass = input("Proxy bypass domains (optional): ").strip()

    save_config(config_path, pat, repo, name, email, claude_oauth, proxy_bypass)
    log_success(f"Config written to {config_path}")
