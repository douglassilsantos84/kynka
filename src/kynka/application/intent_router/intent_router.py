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

    Prioriza intenções empresariais específicas antes
    das intenções genéricas.
    """

    def route(
        self,
        text: str,
    ) -> IntentRoute:

        normalized_text = self._normalize(
            text
        )

        if not normalized_text:
            raise IntentNotFoundError(
                "Não é possível identificar "
                "uma intenção em um texto vazio."
            )

        # ==================================================
        # DADOS EMPRESARIAIS NÃO RELACIONADOS A INVENTÁRIO
        # ==================================================

        if self._is_non_inventory_business_data(
            normalized_text
        ):
            raise IntentNotFoundError(
                "A solicitação depende de uma fonte "
                "empresarial específica."
            )

        # ==================================================
        # INVENTÁRIO
        # ==================================================

        if self._is_inventory_low_stock(
            normalized_text
        ):
            return IntentRoute(
                capability="inventory.low_stock",
                confidence=1.0,
                reason=(
                    "Foi identificada uma consulta "
                    "de materiais abaixo do estoque mínimo."
                ),
            )

        if self._is_inventory_summary(
            normalized_text
        ):
            return IntentRoute(
                capability="inventory.summary",
                confidence=1.0,
                reason=(
                    "Foi identificada uma solicitação "
                    "de resumo do inventário."
                ),
            )

        if self._is_inventory_list(
            normalized_text
        ):
            return IntentRoute(
                capability="inventory.list",
                confidence=1.0,
                reason=(
                    "Foi identificada uma solicitação "
                    "de listagem do inventário."
                ),
            )

        if self._is_inventory_search(
            normalized_text
        ):
            return IntentRoute(
                capability="inventory.search",
                confidence=1.0,
                reason=(
                    "Foi identificada uma consulta "
                    "sobre material em estoque."
                ),
            )

        # ==================================================
        # CALCULADORA
        # ==================================================

        if self._is_multiplication(
            normalized_text
        ):
            return IntentRoute(
                capability="calculator.multiply",
                confidence=1.0,
                reason=(
                    "Foi identificada uma solicitação "
                    "de multiplicação."
                ),
            )

        if self._is_addition(
            normalized_text
        ):
            return IntentRoute(
                capability="calculator.add",
                confidence=1.0,
                reason=(
                    "Foi identificada uma solicitação "
                    "de adição."
                ),
            )

        # ==================================================
        # CUMPRIMENTO
        # ==================================================

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
                    "Foi identificada uma intenção "
                    "de cumprimento."
                ),
            )

        raise IntentNotFoundError(
            "Nenhuma intenção conhecida "
            f"para: {text!r}"
        )

    # ======================================================
    # PROTEÇÃO DE OUTROS DADOS EMPRESARIAIS
    # ======================================================

    @staticmethod
    def _is_non_inventory_business_data(
        text: str,
    ) -> bool:
        """
        Impede que dados financeiros, bancários ou
        administrativos sejam confundidos com estoque.

        Esses pedidos devem seguir para outra Capability
        específica ou para o fallback protegido.
        """

        terms = (
            "conta bancaria",
            "saldo bancario",
            "saldo da conta",
            "saldo em conta",
            "banco da empresa",
            "conta da empresa",
            "faturamento",
            "faturacao",
            "receita da empresa",
            "lucro da empresa",
            "caixa da empresa",
            "saldo de caixa",
            "dinheiro da empresa",
            "folha salarial",
            "salarios da empresa",
            "impostos da empresa",
        )

        return any(
            term in text
            for term in terms
        )

    # ======================================================
    # INVENTÁRIO
    # ======================================================

    @staticmethod
    def _is_inventory_low_stock(
        text: str,
    ) -> bool:

        terms = (
            "abaixo do minimo",
            "abaixo do estoque minimo",
            "abaixo do stock minimo",
            "estoque baixo",
            "stock baixo",
            "baixo estoque",
            "baixo stock",
            "faltando no estoque",
            "faltando no stock",
            "materiais em falta",
            "produtos em falta",
        )

        return any(
            term in text
            for term in terms
        )

    @staticmethod
    def _is_inventory_summary(
        text: str,
    ) -> bool:

        inventory_terms = (
            "estoque",
            "stock",
            "inventario",
        )

        summary_terms = (
            "resumo",
            "situacao",
            "indicadores",
            "visao geral",
            "estado geral",
        )

        return (
            any(
                term in text
                for term in inventory_terms
            )
            and any(
                term in text
                for term in summary_terms
            )
        )

    @staticmethod
    def _is_inventory_list(
        text: str,
    ) -> bool:

        patterns = (
            "liste os materiais",
            "listar materiais",
            "mostre os materiais",
            "mostrar materiais",
            "todos os materiais",
            "listar estoque",
            "listar stock",
            "liste o estoque",
            "liste o stock",
            "mostrar estoque",
            "mostrar stock",
        )

        return any(
            term in text
            for term in patterns
        )

    @staticmethod
    def _is_inventory_search(
        text: str,
    ) -> bool:
        """
        Identifica consultas de materiais.

        A palavra "saldo" isoladamente não é suficiente,
        pois pode representar saldo bancário, caixa etc.
        """

        direct_patterns = (
            "quanto temos de ",
            "quanto tem de ",
            "quanto tenho de ",
            "quantos temos de ",
            "quantas temos de ",
            "qual a quantidade de ",
            "qual quantidade de ",
        )

        if any(
            pattern in text
            for pattern in direct_patterns
        ):
            return True

        inventory_terms = (
            "estoque",
            "stock",
            "inventario",
            "material",
            "materiais",
            "produto",
            "produtos",
        )

        query_terms = (
            "quanto",
            "quantidade",
            "saldo",
            "consulte",
            "consultar",
            "procure",
            "procurar",
            "temos",
            "tem",
        )

        if (
            any(
                term in text
                for term in inventory_terms
            )
            and any(
                term in text
                for term in query_terms
            )
        ):
            return True

        specific_balance_patterns = (
            "saldo do material",
            "saldo de material",
            "saldo do produto",
            "saldo de produto",
            "saldo em estoque",
            "saldo no estoque",
            "saldo em stock",
            "saldo no stock",
        )

        return any(
            pattern in text
            for pattern in specific_balance_patterns
        )

    # ======================================================
    # CALCULADORA
    # ======================================================

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

    # ======================================================
    # NORMALIZAÇÃO
    # ======================================================

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