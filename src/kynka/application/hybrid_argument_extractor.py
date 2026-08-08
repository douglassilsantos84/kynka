"""
Extração híbrida de argumentos da plataforma Kynka.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kynka.application.argument_extractor import (
    ArgumentExtractor,
)
from kynka.domain.plugins.plugin import Plugin


ArgumentExtractionStrategy = Callable[
    [str],
    dict[str, Any],
]


class HybridArgumentExtractor:
    """
    Coordena estratégias determinísticas específicas
    e extração baseada em LLM.

    Estratégias específicas têm prioridade.
    O LLM é utilizado como fallback.
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
        Registra uma estratégia para uma Capability.
        """

        capability_name = capability_name.strip()

        if not capability_name:
            raise ValueError(
                "O nome da Capability não pode estar vazio."
            )

        if not callable(strategy):
            raise TypeError(
                "A estratégia de extração precisa ser executável."
            )

        self._strategies[
            capability_name
        ] = strategy

    def register_plugin(
        self,
        plugin: Plugin,
    ) -> None:
        """
        Registra automaticamente as estratégias
        de extração declaradas por um Plugin.
        """

        strategies = getattr(
            plugin,
            "argument_strategies",
            {},
        )

        for capability_name, strategy in strategies.items():
            self.register(
                capability_name=capability_name,
                strategy=strategy,
            )

    def extract(
        self,
        text: str,
        capability: str,
        parameters: dict[str, str],
    ) -> dict[str, Any]:
        """
        Extrai os argumentos necessários.

        Prioridade:
        1. estratégia específica;
        2. LLM;
        3. nenhum argumento, quando a Capability
           não possui parâmetros.
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
        Retorna os nomes das Capabilities que possuem
        estratégias específicas registradas.
        """

        return tuple(
            self._strategies.keys()
        )