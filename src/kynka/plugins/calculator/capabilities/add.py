"""
Capability de adição da plataforma Kynka.
"""

from __future__ import annotations

from typing import Any

from kynka.domain.capabilities import (
    Capability,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityResult,
)


class AddCapability(Capability):
    """
    Soma dois valores numéricos.
    """

    def __init__(self) -> None:
        super().__init__(
            CapabilityMetadata(
                name="calculator.add",
                description=(
                    "Soma dois números e retorna "
                    "o resultado da adição."
                ),
                version="1.0.0",
                parameters=(
                    CapabilityParameter(
                        name="left",
                        description=(
                            "Primeiro número da adição."
                        ),
                        type="number",
                        required=True,
                    ),
                    CapabilityParameter(
                        name="right",
                        description=(
                            "Segundo número da adição."
                        ),
                        type="number",
                        required=True,
                    ),
                ),
            )
        )

    def execute(
        self,
        **kwargs: Any,
    ) -> CapabilityResult:
        left = kwargs.get("left")
        right = kwargs.get("right")

        if left is None or right is None:
            return CapabilityResult(
                success=False,
                error=(
                    "Os parâmetros 'left' e 'right' "
                    "são obrigatórios."
                ),
            )

        if not isinstance(
            left,
            (int, float),
        ):
            return CapabilityResult(
                success=False,
                error=(
                    "'left' precisa ser um número."
                ),
            )

        if not isinstance(
            right,
            (int, float),
        ):
            return CapabilityResult(
                success=False,
                error=(
                    "'right' precisa ser um número."
                ),
            )

        return CapabilityResult(
            success=True,
            data=left + right,
        )