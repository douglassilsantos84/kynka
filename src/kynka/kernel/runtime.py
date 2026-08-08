"""
Runtime principal da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from kynka.application.intent_router import IntentRouter
from kynka.application.task_executor import TaskExecutor
from kynka.domain.plugins.plugin import Plugin
from kynka.domain.tasks import Task, TaskResult
from kynka.kernel.registry import Registry


@dataclass(slots=True)
class Runtime:
    """
    Controla o ciclo de vida e a execução da plataforma Kynka.
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

        self.registry.register_plugin(plugin)

    def execute(
        self,
        capability: str,
        **kwargs: Any,
    ) -> Any:
        """
        Executa diretamente uma Capability registrada.

        Esta é a API de baixo nível da plataforma.
        """

        capability_object = self.registry.get_capability(
            capability
        )

        return capability_object.execute(
            **kwargs
        )

    def run(
        self,
        task: Task,
    ) -> TaskResult:
        """
        Executa uma Task através do fluxo de roteamento.

        Esta é a API de alto nível para execução orientada
        por intenção.
        """

        router = IntentRouter()

        executor = TaskExecutor(
            registry=self.registry,
            router=router,
        )

        return executor.execute(task)

    @property
    def is_running(self) -> bool:
        """
        Indica se o Runtime está ativo.
        """

        return self.started