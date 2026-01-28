"""Config - typed configuration for a yolo-cage instance."""

from dataclasses import dataclass
from pathlib import Path

from .output import die, log_step, log_success
from .github import validate_github_repo


@dataclass
class Config:
    """Typed configuration for a yolo-cage instance."""

    github_pat: str
    repo_url: str
    git_name: str = "yolo-cage"
    git_email: str = "yolo-cage@localhost"
    proxy_bypass: str = ""

    @classmethod
    def load(cls, path: Path) -> "Config | None":
        """Load from config.env file. Returns None if missing or invalid."""
        if not path.exists():
            return None

        values = {}
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()

        pat = values.get("GITHUB_PAT")
        repo = values.get("REPO_URL")
        if not pat or not repo:
            return None

        return cls(
            github_pat=pat,
            repo_url=repo,
            git_name=values.get("GIT_NAME", "yolo-cage"),
            git_email=values.get("GIT_EMAIL", "yolo-cage@localhost"),
            proxy_bypass=values.get("PROXY_BYPASS", ""),
        )

    def save(self, path: Path) -> None:
        """Write to config.env file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# yolo-cage configuration",
            f"GITHUB_PAT={self.github_pat}",
            f"REPO_URL={self.repo_url}",
            f"GIT_NAME={self.git_name}",
            f"GIT_EMAIL={self.git_email}",
        ]
        if self.proxy_bypass:
            lines.append(f"PROXY_BYPASS={self.proxy_bypass}")
        path.write_text("\n".join(lines) + "\n")

    def validate(self) -> None:
        """Validate GitHub access. Dies on failure."""
        log_step("Validating repository access...")
        valid, message = validate_github_repo(self.repo_url, self.github_pat)
        if not valid:
            die(message)
        log_success(message)

    @classmethod
    def prompt(cls) -> "Config":
        """Interactively prompt user for configuration."""
        print("yolo-cage configuration\n")

        pat = input("GitHub PAT: ").strip()
        if not pat:
            die("GitHub PAT is required")

        repo = input("Repository URL: ").strip()
        if not repo:
            die("Repository URL is required")

        # Validate before asking for optional fields
        log_step("Validating repository access...")
        valid, message = validate_github_repo(repo, pat)
        if not valid:
            die(message)
        log_success(message)

        git_name = input("Git name [yolo-cage]: ").strip() or "yolo-cage"
        git_email = input("Git email [yolo-cage@localhost]: ").strip() or "yolo-cage@localhost"
        proxy_bypass = input("Proxy bypass domains (optional): ").strip()

        return cls(
            github_pat=pat,
            repo_url=repo,
            git_name=git_name,
            git_email=git_email,
            proxy_bypass=proxy_bypass,
        )
