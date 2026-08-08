"""
Roteamento de intenções da plataforma Kynka.
"""

from __future__ import annotations

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

    Nesta primeira versão, o roteamento é determinístico
    e baseado em palavras-chave.
    """

    def route(self, text: str) -> IntentRoute:
        """
        Identifica a Capability adequada para o texto recebido.
        """

        normalized_text = self._normalize(text)

        if not normalized_text:
            raise IntentNotFoundError(
                "Não é possível identificar uma intenção em um texto vazio."
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
                reason="Foi identificada uma intenção de cumprimento.",
            )

        raise IntentNotFoundError(
            f"Nenhuma intenção conhecida para: {text!r}"
        )

    @staticmethod
    def _normalize(text: str) -> str:
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