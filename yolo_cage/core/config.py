"""Config - typed configuration for a yolo-cage instance."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Configuration for a yolo-cage instance."""

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
