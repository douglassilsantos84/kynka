"""
Runtime principal da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from kynka.kernel.registry import Registry


@dataclass(slots=True)
class Runtime:
    """
    Controla o ciclo de vida principal da plataforma.
    """

    started: bool = False
    started_at: datetime | None = None
    registry: Registry = field(default_factory=Registry)

    def start(self) -> None:
        """
        Inicializa o Runtime.
        """
        if self.started:
            return

        self.started = True
        self.started_at = datetime.now()

        print("✓ Runtime iniciado")

    def stop(self) -> None:
        """
        Finaliza o Runtime e descarrega os plugins.
        """
        if not self.started:
            return

        self.registry.unload_plugins()

        self.started = False
        self.started_at = None

        print("✓ Runtime finalizado")

    @property
    def is_running(self) -> bool:
        """
        Indica se o Runtime está ativo.
        """
        return self.started