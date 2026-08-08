"""
Extração determinística de argumentos do Calculator Plugin.
"""

from __future__ import annotations

import re
from typing import Any


class CalculatorArgumentExtractionError(Exception):
    """
    Erro lançado quando não é possível identificar
    os argumentos necessários para uma operação matemática.
    """


class CalculatorArgumentExtractor:
    """
    Extrai argumentos matemáticos diretamente do texto.

    Esta implementação não depende de LLM.
    """

    NUMBER_PATTERN = re.compile(
        r"[-+]?(?:\d+(?:[.,]\d+)?|[.,]\d+)"
    )

    def extract_multiply(
        self,
        text: str,
    ) -> dict[str, Any]:
        """
        Extrai os dois operandos necessários para multiplicação.
        """

        text = text.strip()

        if not text:
            raise CalculatorArgumentExtractionError(
                "Não é possível extrair argumentos de um texto vazio."
            )

        matches = self.NUMBER_PATTERN.findall(
            text
        )

        if len(matches) < 2:
            raise CalculatorArgumentExtractionError(
                "Não foi possível identificar dois números "
                "para a multiplicação."
            )

        if len(matches) > 2:
            raise CalculatorArgumentExtractionError(
                "Foram encontrados mais de dois números "
                "na solicitação."
            )

        left = self._convert_number(
            matches[0]
        )

        right = self._convert_number(
            matches[1]
        )

        return {
            "left": left,
            "right": right,
        }

    @staticmethod
    def _convert_number(
        value: str,
    ) -> int | float:
        """
        Converte representação textual em int ou float.
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