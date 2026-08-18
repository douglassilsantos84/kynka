"""
Entidade Material do domínio de inventário da Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Material:
    """
    Representa um material armazenado no inventário.
    """

    code: str
    name: str
    quantity: float
    unit: str = "un"
    minimum_quantity: float = 0.0

    @property
    def is_below_minimum(self) -> bool:
        """
        Indica se o stock atual está abaixo
        da quantidade mínima definida.
        """

        return self.quantity < self.minimum_quantity