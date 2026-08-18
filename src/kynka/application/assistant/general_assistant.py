"""
Fallback conversacional da plataforma Kynka.
"""

from __future__ import annotations

import unicodedata

from kynka.domain.providers import (
    Provider,
    ProviderRequest,
)


class GeneralAssistantError(Exception):
    """
    Erro durante uma resposta conversacional.
    """


class GeneralAssistant:
    """
    Responde solicitações gerais quando nenhuma
    Capability registrada é adequada.

    Dados empresariais protegidos nunca devem ser
    respondidos pelo modelo sem uma fonte real.
    """

    _PROTECTED_TERMS = (
        "estoque",
        "stock",
        "inventario",
        "inventário",
        "saldo de material",
        "quantidade de material",
        "quantidade em estoque",
        "quantidade em stock",
        "nosso estoque",
        "nosso stock",
        "nossa empresa",
        "da empresa",
        "nosso erp",
        "no erp",
        "saldo da empresa",
        "faturamento da empresa",
        "faturacao da empresa",
        "faturação da empresa",
        "conta bancaria da empresa",
        "conta bancária da empresa",
    )

    def __init__(
        self,
        provider: Provider,
    ) -> None:
        self._provider = provider

    def answer(
        self,
        text: str,
    ) -> str:
        """
        Produz uma resposta de conhecimento geral.
        """

        original_text = text.strip()

        if not original_text:
            raise GeneralAssistantError(
                "A pergunta não pode estar vazia."
            )

        if self.requires_business_source(
            original_text
        ):
            return (
                "Essa solicitação depende de dados reais da empresa. "
                "A Kynka não deve inventar essa informação. "
                "É necessário utilizar uma Capability ou integração "
                "conectada à fonte desses dados."
            )

        prompt = (
            "Você é o assistente geral da plataforma Kynka.\n"
            "\n"
            "Responda à pergunta do usuário de forma clara, "
            "objetiva e em português, salvo se ele pedir outro idioma.\n"
            "\n"
            "REGRAS:\n"
            "- Não invente dados privados ou empresariais.\n"
            "- Não diga que consultou sistemas que não foram fornecidos.\n"
            "- Para conhecimento geral, responda normalmente.\n"
            "- Não descreva o processo interno da plataforma.\n"
            "\n"
            "PERGUNTA:\n"
            f"{original_text}\n"
            "\n"
            "RESPOSTA:"
        )

        response = self._provider.generate(
            ProviderRequest(
                prompt=prompt
            )
        )

        if not response.success:
            raise GeneralAssistantError(
                "O modelo de linguagem não conseguiu responder: "
                f"{response.error}"
            )

        content = (
            response.content or ""
        ).strip()

        if not content:
            raise GeneralAssistantError(
                "O modelo retornou uma resposta vazia."
            )

        return content

    def requires_business_source(
        self,
        text: str,
    ) -> bool:
        """
        Detecta solicitações que dependem de fontes
        empresariais reais.
        """

        normalized = self._normalize(
            text
        )

        protected_terms = tuple(
            self._normalize(term)
            for term in self._PROTECTED_TERMS
        )

        return any(
            term in normalized
            for term in protected_terms
        )

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
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