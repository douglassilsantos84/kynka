"""
Hello Plugin V2.

Primeiro plugin baseado em Capabilities da Kynka.
"""

from __future__ import annotations

from kynka.domain.capabilities import Capability
from kynka.domain.plugins.plugin import Plugin, PluginMetadata

from kynka.plugins.hello.capabilities.hello import HelloCapability


class HelloPluginV2(Plugin):
    """
    Plugin de exemplo da plataforma.
    """

    def __init__(self) -> None:

        super().__init__(
            PluginMetadata(
                name="hello",
                version="2.0.0",
                description="Plugin de exemplo da plataforma.",
                author="Douglas Santos",
                tags=("example", "hello"),
            )
        )

        self._capabilities = [
            HelloCapability(),
        ]

    @property
    def capabilities(self) -> list[Capability]:
        return self._capabilities

    def on_load(self) -> None:
        print("✓ Hello Plugin V2 carregado")

    def on_unload(self) -> None:
        print("✓ Hello Plugin V2 finalizado")