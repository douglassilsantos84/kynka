"""
Estruturas que representam uma etapa de um plano da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ResultReference:
    """
    Referência ao resultado produzido por uma etapa anterior.

    Permite que uma etapa utilize dinamicamente o resultado
    de outra etapa do mesmo plano.
    """

    step_id: str


@dataclass(slots=True)
class PlanStep:
    """
    Representa uma etapa individual de um plano.

    Cada etapa define:

    - um identificador;
    - a Capability que será executada;
    - os argumentos utilizados pela Capability;
    - uma descrição opcional.
    """

    id: str
    capability: str
    arguments: dict[str, Any] = field(
        default_factory=dict
    )
    description: str | None = None

    def __post_init__(self) -> None:
        self.id = self.id.strip()
        self.capability = self.capability.strip()

        if not self.id:
            raise ValueError(
                "O identificador da etapa não pode estar vazio."
            )

        if not self.capability:
            raise ValueError(
                "A Capability da etapa não pode estar vazia."
            )