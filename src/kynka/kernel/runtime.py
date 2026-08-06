"""
Runtime principal da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from kynka.kernel.registry import Registry
from kynka.domain.plugins.plugin import Plugin


@dataclass(slots=True)
class Runtime:

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

    def register_plugin(
        self,
        plugin: Plugin,
    ) -> None:

        self.registry.register_plugin(plugin)

    def execute(
        self,
        capability: str,
        **kwargs: Any,
    ) -> Any:

        capability_object = self.registry.get_capability(
            capability
        )

        return capability_object.execute(
            **kwargs
        )

    @property
    def is_running(self) -> bool:

        return self.started