"""
Inventory Plugin da plataforma Kynka.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kynka.application.inventory import (
    InventoryService,
)
from kynka.domain.capabilities import (
    Capability,
)
from kynka.domain.plugins.plugin import (
    Plugin,
    PluginMetadata,
)

from .argument_extractor import (
    InventoryArgumentExtractor,
)
from .capabilities import (
    InventoryListCapability,
    InventoryLowStockCapability,
    InventorySearchCapability,
    InventorySummaryCapability,
)


ArgumentExtractionStrategy = Callable[
    [str],
    dict[str, Any],
]


class InventoryPlugin(Plugin):
    """
    Plugin responsável pelas operações
    empresariais de inventário.
    """

    def __init__(
        self,
        service: InventoryService,
    ) -> None:

        super().__init__(
            PluginMetadata(
                name="inventory",
                version="1.0.0",
                description=(
                    "Consulta e análise do inventário "
                    "empresarial da Kynka."
                ),
                author="Douglas Santos",
                tags=(
                    "inventory",
                    "stock",
                    "business",
                ),
            )
        )

        self._service = service

        self._capabilities: list[
            Capability
        ] = [
            InventorySearchCapability(
                service
            ),
            InventoryListCapability(
                service
            ),
            InventoryLowStockCapability(
                service
            ),
            InventorySummaryCapability(
                service
            ),
        ]

        extractor = (
            InventoryArgumentExtractor()
        )

        self._argument_strategies: dict[
            str,
            ArgumentExtractionStrategy,
        ] = {
            "inventory.search":
                extractor.extract_search,
        }

    @property
    def capabilities(
        self,
    ) -> list[Capability]:

        return list(
            self._capabilities
        )

    @property
    def argument_strategies(
        self,
    ) -> dict[
        str,
        ArgumentExtractionStrategy,
    ]:

        return dict(
            self._argument_strategies
        )

    def on_load(self) -> None:

        print(
            "✓ Inventory Plugin carregado"
        )

    def on_unload(self) -> None:

        print(
            "✓ Inventory Plugin finalizado"
        )