"""
Metadados de uma Capability.
"""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CapabilityMetadata:
    """
    Informações descritivas da Capability.
    """

    name: str

    description: str

    version: str = "1.0.0"