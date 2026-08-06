"""
Runtime principal da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from kynka.domain.plugins.plugin import Plugin
from kynka.kernel.registry import Registry


@dataclass(slots=True)
class Runtime:
    """
    Controla o ciclo de vida da plataforma.
    """

    started: bool = False
    started_at: datetime | None = None
    registry: Registry = field(default_factory=Registry)

    def start(self) -> None:
        if self.started:
            return

        self.started = True
        self.started_at = datetime.now()

        print("✓ Runtime iniciado")

    def stop(self) -> None:
        if not self.started:
            return

        self.registry.unload_plugins()

        self.started = False
        self.started_at = None

        print("✓ Runtime finalizado")

    def register_plugin(self, plugin: Plugin) -> None:
        """
        Registra um plugin no Runtime.
        """
        self.registry.register_plugin(plugin)

    def execute(
        self,
        plugin_name: str,
        **kwargs: Any,
    ) -> Any:
        """
        Executa um plugin registrado.
        """

        plugin = self.registry.get_plugin(plugin_name)

        return plugin.execute(**kwargs)

    @property
    def is_running(self) -> bool:
        return self.started