"""
Solicitação enviada a um Provider da Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProviderRequest:
    """
    Representa uma solicitação enviada a um Provider.
    """

    prompt: str

    context: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.prompt = self.prompt.strip()

        if not self.prompt:
            raise ValueError(
                "O prompt do Provider não pode estar vazio."
            )