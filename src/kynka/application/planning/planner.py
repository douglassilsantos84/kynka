"""
Planner determinístico da plataforma Kynka.
"""

from __future__ import annotations

import re
import unicodedata

from .plan_step import (
    PlanStep,
    ResultReference,
)
from .task_plan import TaskPlan


class PlanningError(Exception):
    """
    Erro ocorrido durante a criação de um plano.
    """


class DeterministicPlanner:
    """
    Cria planos para solicitações compostas conhecidas.

    Esta primeira implementação reconhece sequências
    matemáticas simples envolvendo adição e multiplicação.
    """

    _NUMBER = r"-?\d+(?:[.,]\d+)?"

    def plan(
        self,
        text: str,
    ) -> TaskPlan:
        """
        Constrói um TaskPlan a partir de linguagem natural.
        """

        original_text = text.strip()

        if not original_text:
            raise PlanningError(
                "Não é possível criar um plano "
                "para uma solicitação vazia."
            )

        normalized = self._normalize(original_text)

        operations = self._extract_operations(
            normalized
        )

        if not operations:
            raise PlanningError(
                "Não foi possível construir um plano "
                f"para: {original_text!r}"
            )

        plan = TaskPlan()

        previous_step_id: str | None = None

        for index, operation in enumerate(
            operations,
            start=1,
        ):
            step_id = f"step{index}"

            capability = operation[
                "capability"
            ]

            left = operation["left"]
            right = operation["right"]

            if left == "__previous__":
                if previous_step_id is None:
                    raise PlanningError(
                        "A operação referencia um "
                        "resultado anterior inexistente."
                    )

                left = ResultReference(
                    previous_step_id
                )

            plan.add_step(
                PlanStep(
                    id=step_id,
                    capability=capability,
                    arguments={
                        "left": left,
                        "right": right,
                    },
                    description=operation[
                        "description"
                    ],
                )
            )

            previous_step_id = step_id

        return plan

    def _extract_operations(
        self,
        text: str,
    ) -> list[dict]:
        """
        Extrai operações sequenciais do texto.
        """

        operations: list[dict] = []

        first_add = re.search(
            rf"(?:some|somar|soma|adicione)"
            rf"\s+({self._NUMBER})"
            rf"\s+(?:mais|com)\s+"
            rf"({self._NUMBER})",
            text,
        )

        first_multiply = re.search(
            rf"(?:multiplique|multiplicar|multiplica)"
            rf"\s+({self._NUMBER})"
            rf"\s+por\s+"
            rf"({self._NUMBER})",
            text,
        )

        first_match = None
        first_type = None

        if first_add:
            first_match = first_add
            first_type = "add"

        if first_multiply and (
            first_match is None
            or first_multiply.start()
            < first_match.start()
        ):
            first_match = first_multiply
            first_type = "multiply"

        if first_match is None:
            return []

        left = self._number(
            first_match.group(1)
        )
        right = self._number(
            first_match.group(2)
        )

        if first_type == "add":
            capability = "calculator.add"
            description = (
                f"Somar {left} e {right}."
            )
        else:
            capability = (
                "calculator.multiply"
            )
            description = (
                f"Multiplicar {left} por {right}."
            )

        operations.append(
            {
                "capability": capability,
                "left": left,
                "right": right,
                "description": description,
            }
        )

        remaining = text[
            first_match.end():
        ]

        continuation_pattern = re.compile(
            rf"(?:depois|entao|e depois|em seguida)?"
            rf"\s*(?:"
            rf"(?P<add>"
            rf"some|somar|adicione)"
            rf"\s+(?:o\s+)?"
            rf"(?:resultado\s+)?"
            rf"(?:mais\s+)?"
            rf"(?P<add_number>{self._NUMBER})"
            rf"|"
            rf"(?P<multiply>"
            rf"multiplique|multiplicar)"
            rf"\s+(?:o\s+)?"
            rf"(?:resultado\s+)?"
            rf"por\s+"
            rf"(?P<multiply_number>{self._NUMBER})"
            rf")"
        )

        for match in (
            continuation_pattern.finditer(
                remaining
            )
        ):
            if match.group("add"):
                number = self._number(
                    match.group(
                        "add_number"
                    )
                )

                operations.append(
                    {
                        "capability":
                            "calculator.add",
                        "left":
                            "__previous__",
                        "right": number,
                        "description":
                            "Somar ao resultado "
                            f"anterior o valor {number}.",
                    }
                )

            elif match.group("multiply"):
                number = self._number(
                    match.group(
                        "multiply_number"
                    )
                )

                operations.append(
                    {
                        "capability":
                            "calculator.multiply",
                        "left":
                            "__previous__",
                        "right": number,
                        "description":
                            "Multiplicar o resultado "
                            f"anterior por {number}.",
                    }
                )

        return operations

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

    @staticmethod
    def _number(
        value: str,
    ) -> int | float:
        value = value.replace(",", ".")

        number = float(value)

        if number.is_integer():
            return int(number)

        return number
