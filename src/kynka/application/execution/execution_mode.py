"""
Seleção do modo de execução da plataforma Kynka.
"""

from __future__ import annotations

import re
import unicodedata
from enum import Enum


class ExecutionMode(str, Enum):
    """
    Modos de execução suportados pela plataforma.
    """

    SIMPLE = "simple"
    PLAN = "plan"


class ExecutionModeSelector:
    """
    Determina se uma solicitação deve ser executada
    diretamente pelo agente ou através de um plano.

    Nesta versão, a decisão é determinística.
    """

    _SEQUENCE_PATTERNS = (
        r"\bdepois\b",
        r"\bem seguida\b",
        r"\bapos isso\b",
        r"\bposteriormente\b",
        r"\bna sequencia\b",
        r"\bpor fim\b",
    )

    def select(
        self,
        text: str,
    ) -> ExecutionMode:
        """
        Seleciona o modo de execução adequado.
        """

        normalized_text = self._normalize(
            text
        )

        if not normalized_text:
            return ExecutionMode.SIMPLE

        if self._contains_sequence(
            normalized_text
        ):
            return ExecutionMode.PLAN

        return ExecutionMode.SIMPLE

    def _contains_sequence(
        self,
        text: str,
    ) -> bool:
        """
        Verifica indicadores linguísticos
        de uma sequência de tarefas.
        """

        return any(
            re.search(pattern, text)
            is not None
            for pattern in self._SEQUENCE_PATTERNS
        )

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        """
        Normaliza o texto para análise.
        """

        text = text.strip().lower()

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