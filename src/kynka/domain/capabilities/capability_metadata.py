"""
Metadados de uma Capability da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass

from kynka.domain.capabilities.capability_parameter import (
    CapabilityParameter,
)


@dataclass(frozen=True, slots=True)
class CapabilityMetadata:
    """
    Informações descritivas de uma Capability.
    """

    name: str
    description: str
    version: str = "1.0.0"
    parameters: tuple[CapabilityParameter, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "O nome da Capability não pode estar vazio."
            )

        if not self.description.strip():
            raise ValueError(
                "A descrição da Capability não pode estar vazia."
            )

        if not self.version.strip():
            raise ValueError(
                "A versão da Capability não pode estar vazia."
            )