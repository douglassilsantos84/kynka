"""
Representação de uma Task da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass(slots=True)
class Task:
    """
    Representa um objetivo solicitado à plataforma.

    A Task descreve o que precisa ser feito, mas não conhece
    qual Capability será utilizada para executar o objetivo.
    """

    text: str

    context: dict[str, Any] = field(
        default_factory=dict
    )

    id: UUID = field(
        default_factory=uuid4
    )

    def __post_init__(self) -> None:
        self.text = self.text.strip()

        if not self.text:
            raise ValueError(
                "O texto da Task não pode estar vazio."
            )