"""
Calculator Plugin da plataforma Kynka.
"""

from __future__ import annotations

from kynka.domain.capabilities import Capability
from kynka.domain.plugins.plugin import (
    Plugin,
    PluginMetadata,
)
from kynka.plugins.calculator.capabilities import (
    MultiplyCapability,
)


class CalculatorPlugin(Plugin):
    """
    Plugin responsável por operações matemáticas.
    """

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="calculator",
                version="1.0.0",
                description=(
                    "Fornece operações matemáticas "
                    "para a plataforma Kynka."
                ),
                author="Douglas Santos",
                tags=(
                    "calculator",
                    "math",
                ),
            )
        )

        self._capabilities = [
            MultiplyCapability(),
        ]

    @property
    def capabilities(self) -> list[Capability]:
        return self._capabilities

    def on_load(self) -> None:
        print("✓ Calculator Plugin carregado")

    def on_unload(self) -> None:
        print("✓ Calculator Plugin finalizado")