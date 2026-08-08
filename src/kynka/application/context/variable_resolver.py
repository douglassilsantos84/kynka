"""
Resolução de variáveis contextuais da plataforma Kynka.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from kynka.application.context.agent_context import (
    AgentContext,
)


class VariableResolutionError(Exception):
    """
    Erro ocorrido durante a resolução
    de variáveis contextuais.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class VariableResolution:
    """
    Resultado da resolução de variáveis.
    """

    original_text: str
    resolved_text: str
    used_variables: bool
    variables: dict[str, Any]


class VariableResolver:
    """
    Resolve nomes de variáveis existentes
    no AgentContext.
    """

    def __init__(
        self,
        context: AgentContext,
    ) -> None:
        self._context = context

    @property
    def context(self) -> AgentContext:
        return self._context

    def resolve(
        self,
        text: str,
    ) -> VariableResolution:
        """
        Substitui variáveis conhecidas
        pelos respectivos valores.
        """

        original_text = text.strip()
        resolved_text = original_text

        used_variables: dict[str, Any] = {}

        if not original_text:
            return VariableResolution(
                original_text=original_text,
                resolved_text=resolved_text,
                used_variables=False,
                variables={},
            )

        variables = self._context.variables

        if not variables:
            return VariableResolution(
                original_text=original_text,
                resolved_text=resolved_text,
                used_variables=False,
                variables={},
            )

        # Nomes maiores primeiro.
        # Evita conflito entre nomes como:
        # total
        # total_final
        variable_names = sorted(
            variables.keys(),
            key=len,
            reverse=True,
        )

        for name in variable_names:
            value = variables[name]

            pattern = re.compile(
                rf"\b{re.escape(name)}\b",
                flags=re.IGNORECASE,
            )

            if not pattern.search(resolved_text):
                continue

            resolved_text = pattern.sub(
                str(value),
                resolved_text,
            )

            used_variables[name] = value

        return VariableResolution(
            original_text=original_text,
            resolved_text=resolved_text,
            used_variables=bool(
                used_variables
            ),
            variables=used_variables,
        )