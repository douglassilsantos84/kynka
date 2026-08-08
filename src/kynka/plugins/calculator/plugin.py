"""
Calculator Plugin da plataforma Kynka.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kynka.domain.capabilities import Capability
from kynka.domain.plugins.plugin import (
    Plugin,
    PluginMetadata,
)
from kynka.plugins.calculator.argument_extractor import (
    CalculatorArgumentExtractor,
)
from kynka.plugins.calculator.capabilities import (
    AddCapability,
    MultiplyCapability,
)


ArgumentExtractionStrategy = Callable[
    [str],
    dict[str, Any],
]


class CalculatorPlugin(Plugin):
    """
    Plugin responsável por operações matemáticas.
    """

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="calculator",
                version="1.1.0",
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
            AddCapability(),
            MultiplyCapability(),
        ]

        extractor = (
            CalculatorArgumentExtractor()
        )

        self._argument_strategies: dict[
            str,
            ArgumentExtractionStrategy,
        ] = {
            "calculator.add": (
                extractor.extract_add
            ),
            "calculator.multiply": (
                extractor.extract_multiply
            ),
        }

    @property
    def capabilities(
        self,
    ) -> list[Capability]:
        return self._capabilities

    @property
    def argument_strategies(
        self,
    ) -> dict[
        str,
        ArgumentExtractionStrategy,
    ]:
        return dict(
            self._argument_strategies
        )

    def on_load(self) -> None:
        print(
            "✓ Calculator Plugin carregado"
        )

    def on_unload(self) -> None:
        print(
            "✓ Calculator Plugin finalizado"
        )