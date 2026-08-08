"""
Resolução de contexto da plataforma Kynka.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from kynka.application.memory import ExecutionMemory


class ContextResolutionError(Exception):
    """
    Erro ocorrido durante a resolução de contexto.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class ContextResolution:
    """
    Resultado da resolução contextual.
    """

    original_text: str
    resolved_text: str
    used_memory: bool
    referenced_value: Any = None


class ContextResolver:
    """
    Resolve referências contextuais utilizando
    a memória da sessão.
    """

    _RESULT_REFERENCES = (
        "esse resultado",
        "este resultado",
        "o resultado",
        "resultado anterior",
        "ultimo resultado",
    )

    def __init__(
        self,
        memory: ExecutionMemory,
    ) -> None:
        self._memory = memory

    def resolve(
        self,
        text: str,
    ) -> ContextResolution:
        """
        Resolve referências ao resultado anterior.
        """

        original_text = text.strip()

        if not original_text:
            return ContextResolution(
                original_text=original_text,
                resolved_text=original_text,
                used_memory=False,
            )

        normalized_text = self._normalize(
            original_text
        )

        reference = self._find_reference(
            normalized_text
        )

        if reference is None:
            return ContextResolution(
                original_text=original_text,
                resolved_text=original_text,
                used_memory=False,
            )

        previous = self._memory.last_successful

        if previous is None:
            raise ContextResolutionError(
                "Não existe um resultado anterior "
                "na memória da sessão."
            )

        if previous.result is None:
            raise ContextResolutionError(
                "A última execução bem-sucedida "
                "não possui resultado utilizável."
            )

        resolved_text = self._replace_reference(
            original_text,
            reference,
            previous.result,
        )

        return ContextResolution(
            original_text=original_text,
            resolved_text=resolved_text,
            used_memory=True,
            referenced_value=previous.result,
        )

    def _find_reference(
        self,
        normalized_text: str,
    ) -> str | None:
        """
        Identifica uma expressão que referencia
        um resultado anterior.
        """

        for reference in self._RESULT_REFERENCES:
            if reference in normalized_text:
                return reference

        return None

    def _replace_reference(
        self,
        original_text: str,
        normalized_reference: str,
        value: Any,
    ) -> str:
        """
        Substitui a referência contextual pelo
        valor obtido da memória.
        """

        normalized_original = self._normalize(
            original_text
        )

        start = normalized_original.find(
            normalized_reference
        )

        if start < 0:
            return original_text

        end = start + len(
            normalized_reference
        )

        return (
            original_text[:start]
            + str(value)
            + original_text[end:]
        )

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        """
        Normaliza texto preservando o comprimento
        necessário para substituição posicional.
        """

        text = text.lower()

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