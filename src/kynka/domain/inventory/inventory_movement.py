"""
Entidades relacionadas às movimentações de inventário.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MovementType(str, Enum):
    """
    Tipos suportados de movimentação de estoque.
    """

    ENTRY = "entry"
    EXIT = "exit"
    ADJUSTMENT = "adjustment"


@dataclass(slots=True)
class InventoryMovement:
    """
    Registro imutável de uma alteração de quantidade.
    """

    material_code: str
    movement_type: MovementType
    quantity: float
    previous_quantity: float
    new_quantity: float
    reason: str = ""
    created_at: datetime | None = None
    id: int | None = None