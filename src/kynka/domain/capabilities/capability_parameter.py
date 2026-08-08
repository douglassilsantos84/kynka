"""
Definição de parâmetros de uma Capability da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CapabilityParameter:
    """
    Descreve um parâmetro aceito por uma Capability.
    """

    name: str
    description: str
    type: str = "string"
    required: bool = True
    default: Any = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "O nome do parâmetro não pode estar vazio."
            )

        if not self.description.strip():
            raise ValueError(
                "A descrição do parâmetro não pode estar vazia."
            )

        if not self.type.strip():
            raise ValueError(
                "O tipo do parâmetro não pode estar vazio."
            )