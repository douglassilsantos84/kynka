"""
Domínio de inventário da plataforma Kynka.
"""

from .inventory_repository import InventoryRepository
from .material import Material

__all__ = [
    "InventoryRepository",
    "Material",
]