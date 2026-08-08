"""
Capability de multiplicação da plataforma Kynka.
"""

from __future__ import annotations

from typing import Any

from kynka.domain.capabilities import (
    Capability,
    CapabilityMetadata,
    CapabilityResult,
)


class MultiplyCapability(Capability):
    """
    Multiplica dois valores numéricos.
    """

    def __init__(self) -> None:
        super().__init__(
            CapabilityMetadata(
                name="calculator.multiply",
                description=(
                    "Multiplica dois números e retorna "
                    "o resultado da multiplicação."
                ),
                version="1.0.0",
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

        if not isinstance(left, (int, float)):
            return CapabilityResult(
                success=False,
                error="'left' precisa ser um número.",
            )

        if not isinstance(right, (int, float)):
            return CapabilityResult(
                success=False,
                error="'right' precisa ser um número.",
            )

        result = left * right

        return CapabilityResult(
            success=True,
            data=result,
        )