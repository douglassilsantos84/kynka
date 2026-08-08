"""
Roteamento determinístico de intenções da plataforma Kynka.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


class IntentNotFoundError(Exception):
    """
    Erro lançado quando nenhuma intenção pode ser identificada.
    """


@dataclass(frozen=True, slots=True)
class IntentRoute:
    """
    Representa o resultado do roteamento de uma intenção.
    """

    capability: str
    confidence: float
    reason: str


class IntentRouter:
    """
    Responsável por transformar uma solicitação textual
    em uma Capability conhecida pela plataforma.

    O roteamento desta classe é determinístico.
    """

    def route(
        self,
        text: str,
    ) -> IntentRoute:
        """
        Identifica uma Capability através de regras determinísticas.
        """

        normalized_text = self._normalize(text)

        if not normalized_text:
            raise IntentNotFoundError(
                "Não é possível identificar uma intenção "
                "em um texto vazio."
            )

        calculator_route = self._route_calculator(
            normalized_text
        )

        if calculator_route is not None:
            return calculator_route

        greeting_route = self._route_greeting(
            normalized_text
        )

        if greeting_route is not None:
            return greeting_route

        raise IntentNotFoundError(
            f"Nenhuma intenção conhecida para: {text!r}"
        )

    @staticmethod
    def _route_calculator(
        text: str,
    ) -> IntentRoute | None:
        """
        Identifica solicitações explícitas de multiplicação.
        """

        multiplication_terms = (
            "multiplique",
            "multiplicar",
            "multiplicacao",
            "vezes",
        )

        has_multiplication_term = any(
            term in text
            for term in multiplication_terms
        )

        if not has_multiplication_term:
            return None

        numbers = re.findall(
            r"[-+]?(?:\d+(?:[.,]\d+)?|[.,]\d+)",
            text,
        )

        if len(numbers) < 2:
            return None

        return IntentRoute(
            capability="calculator.multiply",
            confidence=1.0,
            reason=(
                "Foi identificada uma solicitação "
                "explícita de multiplicação."
            ),
        )

    @staticmethod
    def _route_greeting(
        text: str,
    ) -> IntentRoute | None:
        """
        Identifica solicitações de cumprimento.
        """

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

        if not any(
            term in text
            for term in greeting_terms
        ):
            return None

        return IntentRoute(
            capability="greeting.hello",
            confidence=1.0,
            reason=(
                "Foi identificada uma intenção "
                "de cumprimento."
            ),
        )

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        """
        Normaliza o texto para facilitar o roteamento.
        """

        text = text.strip().lower()

        normalized = unicodedata.normalize(
            "NFKD",
            text,
        )

        return "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )