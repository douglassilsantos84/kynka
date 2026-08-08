"""
Comandos de manipulação do contexto da plataforma Kynka.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from kynka.application.context.agent_context import (
    AgentContext,
)


class ContextCommandError(Exception):
    """
    Erro ocorrido durante a execução
    de um comando contextual.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class ContextCommandResult:
    """
    Resultado da execução de um
    comando contextual.
    """

    handled: bool
    success: bool
    message: str | None = None
    variable: str | None = None
    value: Any = None
    error: str | None = None


class ContextCommandHandler:
    """
    Interpreta comandos explícitos relacionados
    ao estado do AgentContext.
    """

    def __init__(
        self,
        context: AgentContext,
    ) -> None:
        self._context = context

    @property
    def context(self) -> AgentContext:
        return self._context

    def handle(
        self,
        text: str,
    ) -> ContextCommandResult:
        """
        Tenta interpretar o texto como
        um comando contextual.
        """

        original_text = text.strip()

        if not original_text:
            return self._not_handled()

        normalized_text = self._normalize(
            original_text
        )

        variable_name = (
            self._extract_store_last_result(
                normalized_text
            )
        )

        if variable_name is not None:
            return self._store_last_result(
                variable_name
            )

        return self._not_handled()

    def _store_last_result(
        self,
        variable_name: str,
    ) -> ContextCommandResult:
        """
        Armazena o último resultado bem-sucedido
        em uma variável contextual.
        """

        value = self._context.last_result

        if value is None:
            return ContextCommandResult(
                handled=True,
                success=False,
                variable=variable_name,
                error=(
                    "Não existe um resultado anterior "
                    "para armazenar."
                ),
            )

        try:
            self._context.set_variable(
                variable_name,
                value,
            )

        except (ValueError, TypeError) as error:
            return ContextCommandResult(
                handled=True,
                success=False,
                variable=variable_name,
                error=str(error),
            )

        return ContextCommandResult(
            handled=True,
            success=True,
            message=(
                f"{variable_name} = {value}"
            ),
            variable=variable_name,
            value=value,
        )

    @staticmethod
    def _extract_store_last_result(
        normalized_text: str,
    ) -> str | None:
        """
        Identifica comandos como:

        guarde esse resultado como total
        guardar esse resultado como total
        salve esse resultado como total
        salvar esse resultado como total
        """
        
        patterns = (
            (
                r"^(?:guarde|guardar|salve|salvar)"
                r"\s+(?:esse|este|o)\s+resultado"
                r"\s+como\s+([a-z_][a-z0-9_]*)$"
            ),
            (
                r"^(?:guarde|guardar|salve|salvar)"
                r"\s+resultado\s+como"
                r"\s+([a-z_][a-z0-9_]*)$"
            ),
        )

        for pattern in patterns:
            match = re.fullmatch(
                pattern,
                normalized_text,
            )

            if match is not None:
                return match.group(1)

        return None

    @staticmethod
    def _not_handled() -> ContextCommandResult:
        return ContextCommandResult(
            handled=False,
            success=False,
        )

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        """
        Normaliza caixa, espaços e acentuação.
        """

        text = " ".join(
            text.strip().lower().split()
        )

        normalized = unicodedata.normalize(
            "NFKD",
            text,
        )

        return "".join(
            character
            for character in normalized
            if not unicodedata.combining(
                character
            )
        )