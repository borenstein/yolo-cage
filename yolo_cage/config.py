"""Configuration management."""

from pathlib import Path

from .output import die, log_step, log_success
from .github import validate_github_repo


def load_config(config_path: Path) -> dict[str, str]:
    """Load configuration from config.env file."""
    if not config_path.exists():
        return {}

    config = {}
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def _prompt_required(prompt: str, error: str) -> str:
    value = input(prompt).strip()
    if not value:
        die(error)
    return value


def _prompt_optional(prompt: str, default: str) -> str:
    return input(prompt).strip() or default


def _validate_repo_access(repo_url: str, pat: str) -> None:
    log_step("Validating repository access...")
    valid, message = validate_github_repo(repo_url, pat)
    if not valid:
        die(message)
    log_success(message)


def _write_config(path: Path, pat: str, repo: str, name: str, email: str, bypass: str) -> None:
    with open(path, "w") as f:
        f.write("# yolo-cage configuration\n")
        f.write(f"GITHUB_PAT={pat}\n")
        f.write(f"REPO_URL={repo}\n")
        f.write(f"GIT_NAME={name}\n")
        f.write(f"GIT_EMAIL={email}\n")
        if bypass:
            f.write(f"PROXY_BYPASS={bypass}\n")
    log_success(f"Config written to {path}")


def prompt_config(config_path: Path) -> None:
    """Interactively prompt for configuration."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    print("yolo-cage configuration\n")

    pat = _prompt_required("GitHub PAT: ", "GitHub PAT is required")
    repo = _prompt_required("Repository URL: ", "Repository URL is required")
    _validate_repo_access(repo, pat)

    name = _prompt_optional("Git name [yolo-cage]: ", "yolo-cage")
    email = _prompt_optional("Git email [yolo-cage@localhost]: ", "yolo-cage@localhost")
    bypass = input("Proxy bypass domains (optional): ").strip()

    _write_config(config_path, pat, repo, name, email, bypass)
