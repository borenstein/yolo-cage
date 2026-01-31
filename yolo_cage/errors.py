"""Custom exceptions for yolo-cage."""


class YoloCageError(Exception):
    """Base exception for all yolo-cage errors."""
    pass


class ConfigError(YoloCageError):
    """Configuration-related error."""
    pass


class VMError(YoloCageError):
    """VM-related error."""
    pass


class VMNotRunningError(VMError):
    """VM is not running when it should be."""
    pass


class SandboxError(YoloCageError):
    """Sandbox-related error."""
    pass


class SandboxNotFoundError(SandboxError):
    """Sandbox does not exist."""
    pass


class SandboxAlreadyExistsError(SandboxError):
    """Sandbox already exists for the specified branch."""
    pass


class DispatcherError(YoloCageError):
    """Dispatcher communication error."""
    pass


class KubernetesError(YoloCageError):
    """Kubernetes operation error."""
    pass


class GitHubAPIError(YoloCageError):
    """GitHub API error."""
    pass
