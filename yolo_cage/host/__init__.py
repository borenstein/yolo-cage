"""Host-side operations - VM lifecycle, configuration, delegation to VM."""

from yolo_cage.host.instance import Instance
from yolo_cage.host.registry import (
    AmbiguousInstanceError,
    InstanceExistsError,
    InstanceNotFoundError,
    NoInstancesError,
    Registry,
    RegistryError,
)

__all__ = [
    "Instance",
    "Registry",
    "RegistryError",
    "NoInstancesError",
    "AmbiguousInstanceError",
    "InstanceNotFoundError",
    "InstanceExistsError",
]
