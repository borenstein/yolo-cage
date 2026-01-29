"""Interactive prompts for yolo-cage CLI."""

from ..core import Config
from ..ops import validate_github_repo
from ..output import die, log_step, log_success


def prompt_config() -> Config:
    """Prompt user for configuration interactively."""
    print("yolo-cage configuration\n")

    pat = input("GitHub PAT: ").strip()
    if not pat:
        die("GitHub PAT is required")

    repo = input("Repository URL: ").strip()
    if not repo:
        die("Repository URL is required")

    log_step("Validating repository access...")
    valid, message = validate_github_repo(repo, pat)
    if not valid:
        die(message)
    log_success(message)

    git_name = input("Git name [yolo-cage]: ").strip() or "yolo-cage"
    git_email = input("Git email [yolo-cage@localhost]: ").strip() or "yolo-cage@localhost"
    proxy_bypass = input("Proxy bypass domains (optional): ").strip()

    return Config(
        github_pat=pat,
        repo_url=repo,
        git_name=git_name,
        git_email=git_email,
        proxy_bypass=proxy_bypass,
    )
