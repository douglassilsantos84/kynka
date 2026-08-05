"""
Plugin de demonstração da plataforma Kynka.
"""

from __future__ import annotations

from typing import Any

from kynka.domain.plugins.plugin import Plugin, PluginMetadata


class HelloPlugin(Plugin):
    """
    Primeiro plugin funcional da plataforma.
    """

    def __init__(self) -> None:
        metadata = PluginMetadata(
            name="hello",
            version="1.0.0",
            description="Plugin de demonstração da plataforma Kynka.",
            author="Douglas Santos",
            tags=("example", "hello"),
        )

        super().__init__(metadata=metadata)

    def on_load(self) -> None:
        print("✓ Hello Plugin carregado")

    def on_unload(self) -> None:
        print("✓ Hello Plugin finalizado")

    def execute(self, **kwargs: Any) -> str:
        name = str(kwargs.get("name", "Douglas"))

        return f"Olá, {name}! Mensagem enviada pelo Hello Plugin."