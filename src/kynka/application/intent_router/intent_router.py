"""
Roteamento determinístico de intenções da Kynka.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


class IntentNotFoundError(Exception):
    """
    Nenhuma intenção conhecida foi identificada.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class IntentRoute:
    """
    Resultado do roteamento de uma intenção.
    """

    capability: str
    confidence: float
    reason: str


class IntentRouter:
    """
    Roteador determinístico baseado em regras.
    """

    def route(
        self,
        text: str,
    ) -> IntentRoute:
        """
        Identifica uma Capability conhecida.
        """

        normalized_text = self._normalize(
            text
        )

        if not normalized_text:
            raise IntentNotFoundError(
                "Não é possível identificar "
                "uma intenção em um texto vazio."
            )

        if self._is_multiplication(
            normalized_text
        ):
            return IntentRoute(
                capability=(
                    "calculator.multiply"
                ),
                confidence=1.0,
                reason=(
                    "Foi identificada uma "
                    "solicitação de multiplicação."
                ),
            )

        if self._is_addition(
            normalized_text
        ):
            return IntentRoute(
                capability="calculator.add",
                confidence=1.0,
                reason=(
                    "Foi identificada uma "
                    "solicitação de adição."
                ),
            )

        greeting_terms = (
            "ola",
            "oi",
            "bom dia",
            "boa tarde",
            "boa noite",
            "cumprimente",
            "cumprimentar",
            "diga ola",
        )

        if any(
            term in normalized_text
            for term in greeting_terms
        ):
            return IntentRoute(
                capability="greeting.hello",
                confidence=1.0,
                reason=(
                    "Foi identificada uma "
                    "intenção de cumprimento."
                ),
            )

        raise IntentNotFoundError(
            "Nenhuma intenção conhecida "
            f"para: {text!r}"
        )

    @staticmethod
    def _is_multiplication(
        text: str,
    ) -> bool:
        terms = (
            "multiplique",
            "multiplicar",
            "multiplicacao",
            "vezes",
        )

        if any(
            term in text
            for term in terms
        ):
            return True

        return bool(
            re.search(
                r"\d+(?:[.,]\d+)?\s*\*\s*"
                r"\d+(?:[.,]\d+)?",
                text,
            )
        )

    @staticmethod
    def _is_addition(
        text: str,
    ) -> bool:
        terms = (
            "some",
            "somar",
            "soma",
            "adicione",
            "adicionar",
            "adicao",
            "mais",
        )

        if any(
            term in text
            for term in terms
        ):
            return True

        return bool(
            re.search(
                r"\d+(?:[.,]\d+)?\s*\+\s*"
                r"\d+(?:[.,]\d+)?",
                text,
            )
        )

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
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