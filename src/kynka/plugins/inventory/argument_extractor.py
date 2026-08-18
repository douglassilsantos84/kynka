"""
Extração determinística de argumentos
do Inventory Plugin.
"""

from __future__ import annotations

import re


class InventoryArgumentExtractionError(
    Exception
):
    """
    Erro durante a extração de argumentos
    de uma consulta de inventário.
    """


class InventoryArgumentExtractor:
    """
    Extrai o termo pesquisado em consultas
    de inventário.
    """

    def extract_search(
        self,
        text: str,
    ) -> dict[str, str]:

        original = " ".join(
            text.strip().split()
        )

        if not original:
            raise InventoryArgumentExtractionError(
                "A consulta de estoque está vazia."
            )

        patterns = (
            (
                r"(?i)^quanto\s+(?:temos|tem|tenho)"
                r"\s+(?:de\s+)?(.+?)\??$"
            ),
            (
                r"(?i)^quantos?\s+(.+?)"
                r"\s+(?:temos|tem|existem?)\??$"
            ),
            (
                r"(?i)^qual\s+(?:e\s+)?(?:a\s+)?"
                r"quantidade\s+(?:de\s+)?(.+?)\??$"
            ),
            (
                r"(?i)^(?:consulte|consultar|procure|procurar)"
                r"\s+(?:o\s+|a\s+|por\s+)?(.+?)\??$"
            ),
        )

        query: str | None = None

        for pattern in patterns:
            match = re.match(
                pattern,
                original,
            )

            if match:
                query = match.group(1)
                break

        if query is None:
            query = original

        query = self._clean_query(
            query
        )

        if not query:
            raise InventoryArgumentExtractionError(
                "Não foi possível identificar "
                "o material consultado."
            )

        return {
            "query": query
        }

    @staticmethod
    def _clean_query(
        query: str,
    ) -> str:

        query = query.strip(
            " \t\r\n?.!,;:"
        )

        query = re.sub(
            r"(?i)\s+(?:no|na|do|da)\s+"
            r"(?:estoque|stock|inventario)$",
            "",
            query,
        )

        query = re.sub(
            r"(?i)^(?:o|a|os|as)\s+",
            "",
            query,
        )

        return query.strip()