"""
Extração determinística de argumentos
do Calculator Plugin.
"""

from __future__ import annotations

import re
from typing import Any


class CalculatorArgumentExtractionError(
    Exception
):
    """
    Erro na extração de argumentos matemáticos.
    """


class CalculatorArgumentExtractor:
    """
    Extrai números de solicitações destinadas
    às Capabilities do Calculator Plugin.
    """

    def extract_add(
        self,
        text: str,
    ) -> dict[str, Any]:
        """
        Extrai os dois operandos de uma adição.
        """

        return self._extract_two_numbers(
            text
        )

    def extract_multiply(
        self,
        text: str,
    ) -> dict[str, Any]:
        """
        Extrai os dois operandos de uma multiplicação.
        """

        return self._extract_two_numbers(
            text
        )

    def _extract_two_numbers(
        self,
        text: str,
    ) -> dict[str, Any]:
        """
        Localiza exatamente os dois primeiros
        valores numéricos presentes no texto.
        """

        matches = re.findall(
            r"[-+]?\d+(?:[.,]\d+)?",
            text,
        )

        if len(matches) < 2:
            raise CalculatorArgumentExtractionError(
                "Não foi possível identificar "
                "dois números na solicitação."
            )

        left = self._parse_number(
            matches[0]
        )

        right = self._parse_number(
            matches[1]
        )

        return {
            "left": left,
            "right": right,
        }

    @staticmethod
    def _parse_number(
        value: str,
    ) -> int | float:
        """
        Converte uma representação textual
        em int ou float.
        """

        normalized = value.replace(
            ",",
            ".",
        )

        number = float(
            normalized
        )

        if number.is_integer():
            return int(number)

        return number