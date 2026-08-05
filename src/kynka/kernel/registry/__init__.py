"""
Registry da plataforma Kynka.
"""

from kynka.kernel.registry.registry import (
    ComponentAlreadyRegisteredError,
    ComponentNotFoundError,
    Registry,
    RegistryError,
)

__all__ = [
    "ComponentAlreadyRegisteredError",
    "ComponentNotFoundError",
    "Registry",
    "RegistryError",
]