"""Configuration value object - User credentials and settings."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Config:
    """yolo-cage configuration.

    Attributes:
        github_pat: GitHub Personal Access Token (required)
        repo_url: URL of managed repository (required)
        git_name: Git commit author name (optional)
        git_email: Git commit author email (optional)
        claude_oauth: Claude OAuth token (optional)
        proxy_bypass: Comma-separated domains that bypass egress proxy (optional)
    """

    github_pat: str
    repo_url: str
    git_name: str = "yolo-cage"
    git_email: str = "yolo-cage@localhost"
    claude_oauth: Optional[str] = None
    proxy_bypass: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.github_pat:
            raise ValueError("GITHUB_PAT is required")
        if not self.repo_url:
            raise ValueError("REPO_URL is required")

    @classmethod
    def load(cls, config_path: Path) -> "Config":
        """Load configuration from config.env file.

        Args:
            config_path: Path to config.env file

        Returns:
            Config instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required fields are missing
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        config_dict = {}
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config_dict[key.strip()] = value.strip()

        return cls(
            github_pat=config_dict.get("GITHUB_PAT", ""),
            repo_url=config_dict.get("REPO_URL", ""),
            git_name=config_dict.get("GIT_NAME", "yolo-cage"),
            git_email=config_dict.get("GIT_EMAIL", "yolo-cage@localhost"),
            claude_oauth=config_dict.get("CLAUDE_OAUTH"),
            proxy_bypass=config_dict.get("PROXY_BYPASS"),
        )

    def save(self, config_path: Path) -> None:
        """Save configuration to config.env file.

        Args:
            config_path: Path to write config.env
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            f.write("# yolo-cage configuration\n\n")
            f.write("# Required\n")
            f.write(f"GITHUB_PAT={self.github_pat}\n")
            f.write(f"REPO_URL={self.repo_url}\n\n")
            f.write("# Git identity\n")
            f.write(f"GIT_NAME={self.git_name}\n")
            f.write(f"GIT_EMAIL={self.git_email}\n")

            if self.claude_oauth:
                f.write(f"\nCLAUDE_OAUTH={self.claude_oauth}\n")

            if self.proxy_bypass:
                f.write(f"\nPROXY_BYPASS={self.proxy_bypass}\n")
