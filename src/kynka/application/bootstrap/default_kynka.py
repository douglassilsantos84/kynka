"""
Bootstrap padrão da plataforma Kynka.

Centraliza a construção da aplicação com os
plugins e serviços oficiais.
"""

from __future__ import annotations

from pathlib import Path

from kynka import Kynka
from kynka.application.inventory import InventoryService
from kynka.infrastructure.inventory import (
    SQLiteInventoryRepository,
)
from kynka.plugins.calculator import CalculatorPlugin
from kynka.plugins.hello.plugin_v2 import HelloPluginV2
from kynka.plugins.inventory import InventoryPlugin


DEFAULT_DATABASE_PATH = Path("data/kynka.db")


def build_default_kynka(
    *,
    model: str = "llama3.2:3b",
    memory_size: int = 100,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    start: bool = True,
) -> Kynka:
    """
    Constrói uma instância padrão da Kynka.

    A instância inclui:

    - Runtime;
    - Hello Plugin;
    - Calculator Plugin;
    - Inventory Plugin;
    - SQLite persistente.
    """

    kynka = Kynka(
        model=model,
        memory_size=memory_size,
    )

    if start:
        kynka.start()

    kynka.install(
        HelloPluginV2()
    )

    kynka.install(
        CalculatorPlugin()
    )

    repository = SQLiteInventoryRepository(
        database_path
    )

    inventory_service = InventoryService(
        repository
    )

    kynka.install(
        InventoryPlugin(
            inventory_service
        )
    )

    return kynka