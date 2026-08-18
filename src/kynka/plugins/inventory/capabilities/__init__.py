"""
Capabilities do Inventory Plugin.
"""

from .inventory_capabilities import (
    InventoryListCapability,
    InventoryLowStockCapability,
    InventorySearchCapability,
    InventorySummaryCapability,
)

__all__ = [
    "InventoryListCapability",
    "InventoryLowStockCapability",
    "InventorySearchCapability",
    "InventorySummaryCapability",
]