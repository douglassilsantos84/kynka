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
    Controla o ciclo de vida e a execução de baixo nível
    da plataforma Kynka.

    Responsabilidades:

    - iniciar e finalizar o Runtime;
    - manter o Registry;
    - registrar Plugins;
    - executar Capabilities registradas.

    O Runtime não realiza roteamento de intenções,
    planejamento ou gerenciamento de contexto.
    Essas responsabilidades pertencem à camada
    de Application e à fachada Kynka.
    """

    started: bool = False

    started_at: datetime | None = None

    registry: Registry = field(
        default_factory=Registry
    )

    def start(self) -> None:
        """
        Inicia o Runtime.
        """

        if self.started:
            return

        self.started = True
        self.started_at = datetime.now()

        print("✓ Runtime iniciado")

    def stop(self) -> None:
        """
        Finaliza o Runtime e descarrega os Plugins.
        """

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
        """
        Registra um Plugin na plataforma.
        """

        self.registry.register_plugin(
            plugin
        )

    def execute(
        self,
        capability: str,
        **kwargs: Any,
    ) -> Any:
        """
        Executa diretamente uma Capability registrada.

        Esta é a API de baixo nível do Runtime.
        """

        if not self.started:
            raise RuntimeError(
                "O Runtime da Kynka não está iniciado."
            )

        capability_object = (
            self.registry.get_capability(
                capability
            )
        )

        return capability_object.execute(
            **kwargs
        )

    @property
    def is_running(self) -> bool:
        """
        Indica se o Runtime está ativo.
        """

        return self.started