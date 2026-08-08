"""
Executor de Tasks da plataforma Kynka.
"""

from __future__ import annotations

from kynka.application.intent_router import (
    IntentNotFoundError,
    IntentRouter,
)
from kynka.domain.tasks import Task, TaskResult
from kynka.kernel.registry import Registry


class TaskExecutor:
    """
    Orquestra a execução de uma Task.

    Responsabilidades:
    - receber uma Task;
    - identificar a Capability adequada;
    - localizar a Capability no Registry;
    - executá-la;
    - transformar o resultado em TaskResult.
    """

    def __init__(
        self,
        registry: Registry,
        router: IntentRouter,
    ) -> None:
        self._registry = registry
        self._router = router

    def execute(
        self,
        task: Task,
    ) -> TaskResult:
        try:
            route = self._router.route(task.text)

            capability = self._registry.get_capability(
                route.capability
            )

            capability_result = capability.execute(
                **task.context
            )

            return TaskResult(
                task_id=task.id,
                success=capability_result.success,
                data=capability_result.data,
                error=capability_result.error,
                capability=route.capability,
            )

        except IntentNotFoundError as error:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(error),
            )

        except KeyError as error:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=(
                    "A Capability selecionada não está "
                    f"registrada: {error}"
                ),
            )