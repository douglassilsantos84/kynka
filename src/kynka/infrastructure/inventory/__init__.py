"""
Infraestrutura de inventário da plataforma Kynka.
"""

from .sqlite_inventory_repository import (
    SQLiteInventoryRepository,
)

__all__ = [
    "SQLiteInventoryRepository",
]