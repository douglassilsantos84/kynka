"""
Primeira Capability oficial da plataforma Kynka.
"""

from __future__ import annotations

from typing import Any

from kynka.domain.capabilities import (
    Capability,
    CapabilityMetadata,
    CapabilityResult,
)


class HelloCapability(Capability):
    """
    Capability responsável por cumprimentar o usuário.
    """

    def __init__(self) -> None:

        super().__init__(
            CapabilityMetadata(
                name="greeting.hello",
                description="Cumprimenta um usuário.",
            )
        )

    def execute(
        self,
        **kwargs: Any,
    ) -> CapabilityResult:

        name = kwargs.get("name", "Douglas")

        return CapabilityResult(
            success=True,
            data=f"Olá, {name}! Bem-vindo à Kynka."
        )