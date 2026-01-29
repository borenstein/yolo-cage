"""Exception hierarchy for yolo-cage."""


class YoloCageError(Exception):
    """Base exception for yolo-cage errors."""


class InstanceNotFound(YoloCageError):
    """Requested instance does not exist."""


class InstanceExists(YoloCageError):
    """Instance already exists."""


class NoDefaultInstance(YoloCageError):
    """No default instance set and none specified."""


class VMNotRunning(YoloCageError):
    """VM is not running."""


class VMNotFound(YoloCageError):
    """VM/repository not found."""


class ConfigError(YoloCageError):
    """Configuration error."""


class GitHubAccessError(YoloCageError):
    """GitHub repository access error."""


class PrerequisitesMissing(YoloCageError):
    """Required dependencies are missing."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing prerequisites: {', '.join(missing)}")
