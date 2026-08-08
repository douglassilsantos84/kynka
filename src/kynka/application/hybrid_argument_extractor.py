"""
Extração híbrida de argumentos da plataforma Kynka.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kynka.application.argument_extractor import (
    ArgumentExtractor,
)


ArgumentExtractionStrategy = Callable[
    [str],
    dict[str, Any],
]


class HybridArgumentExtractor:
    """
    Coordena estratégias específicas e extração por LLM.

    Uma Capability pode possuir um extrator determinístico
    registrado. Caso não possua, o ArgumentExtractor baseado
    em Provider é utilizado como fallback.
    """

    def __init__(
        self,
        llm_extractor: ArgumentExtractor,
    ) -> None:
        self._llm_extractor = llm_extractor

        self._strategies: dict[
            str,
            ArgumentExtractionStrategy,
        ] = {}

    def register(
        self,
        capability_name: str,
        strategy: ArgumentExtractionStrategy,
    ) -> None:
        """
        Registra uma estratégia específica para uma Capability.
        """

        capability_name = capability_name.strip()

        if not capability_name:
            raise ValueError(
                "O nome da Capability não pode estar vazio."
            )

        self._strategies[
            capability_name
        ] = strategy

    def extract(
        self,
        text: str,
        capability: str,
        parameters: dict[str, str],
    ) -> dict[str, Any]:
        """
        Extrai argumentos usando primeiro uma estratégia
        específica e depois o LLM como fallback.
        """

        strategy = self._strategies.get(
            capability
        )

        if strategy is not None:
            return strategy(text)

        if not parameters:
            return {}

        return self._llm_extractor.extract(
            text=text,
            capability=capability,
            parameters=parameters,
        )

    @property
    def strategies(
        self,
    ) -> tuple[str, ...]:
        """
        Retorna as Capabilities que possuem
        estratégia específica registrada.
        """

        return tuple(
            self._strategies.keys()
        )