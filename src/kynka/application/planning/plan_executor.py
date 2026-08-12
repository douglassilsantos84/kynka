"""
Executor de planos da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kynka.application.planning.plan_step import (
    PlanStep,
    ResultReference,
)
from kynka.application.planning.task_plan import (
    TaskPlan,
)
from kynka.domain.capabilities import CapabilityResult
from kynka.kernel.runtime import Runtime


class PlanExecutionError(Exception):
    """
    Erro ocorrido durante a execução de um plano.
    """


@dataclass(slots=True)
class PlanStepExecution:
    """
    Resultado da execução de uma etapa do plano.
    """

    step_id: str
    capability: str
    arguments: dict[str, Any]
    success: bool
    result: Any = None
    error: str | None = None


@dataclass(slots=True)
class PlanExecutionResult:
    """
    Resultado completo da execução de um plano.
    """

    success: bool
    steps: list[PlanStepExecution] = field(
        default_factory=list
    )
    result: Any = None
    error: str | None = None


class PlanExecutor:
    """
    Executa planos compostos por múltiplas etapas.

    Cada etapa pode utilizar resultados produzidos
    por etapas anteriores através de ResultReference.
    """

    def __init__(
        self,
        runtime: Runtime,
    ) -> None:
        self._runtime = runtime

    def execute(
        self,
        plan: TaskPlan,
    ) -> PlanExecutionResult:
        """
        Executa todas as etapas de um plano
        na ordem em que foram definidas.
        """

        if len(plan) == 0:
            return PlanExecutionResult(
                success=False,
                error="O plano não possui etapas.",
            )

        results: dict[str, Any] = {}
        executions: list[PlanStepExecution] = []

        for step in plan:
            try:
                arguments = self._resolve_arguments(
                    step=step,
                    results=results,
                )

            except PlanExecutionError as error:
                execution = PlanStepExecution(
                    step_id=step.id,
                    capability=step.capability,
                    arguments={},
                    success=False,
                    error=str(error),
                )

                executions.append(execution)

                return PlanExecutionResult(
                    success=False,
                    steps=executions,
                    error=str(error),
                )

            try:
                capability_result = (
                    self._runtime.execute(
                        step.capability,
                        **arguments,
                    )
                )

            except Exception as error:
                execution = PlanStepExecution(
                    step_id=step.id,
                    capability=step.capability,
                    arguments=arguments,
                    success=False,
                    error=str(error),
                )

                executions.append(execution)

                return PlanExecutionResult(
                    success=False,
                    steps=executions,
                    error=str(error),
                )

            if isinstance(
                capability_result,
                CapabilityResult,
            ):
                execution = PlanStepExecution(
                    step_id=step.id,
                    capability=step.capability,
                    arguments=arguments,
                    success=capability_result.success,
                    result=capability_result.data,
                    error=capability_result.error,
                )

                executions.append(execution)

                if not capability_result.success:
                    return PlanExecutionResult(
                        success=False,
                        steps=executions,
                        error=capability_result.error,
                    )

                result_value = capability_result.data

            else:
                execution = PlanStepExecution(
                    step_id=step.id,
                    capability=step.capability,
                    arguments=arguments,
                    success=True,
                    result=capability_result,
                )

                executions.append(execution)

                result_value = capability_result

            results[step.id] = result_value

        final_result = executions[-1].result

        return PlanExecutionResult(
            success=True,
            steps=executions,
            result=final_result,
        )

    def _resolve_arguments(
        self,
        step: PlanStep,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Resolve ResultReference existentes
        nos argumentos de uma etapa.
        """

        resolved: dict[str, Any] = {}

        for name, value in step.arguments.items():
            resolved[name] = self._resolve_value(
                value=value,
                results=results,
            )

        return resolved

    def _resolve_value(
        self,
        value: Any,
        results: dict[str, Any],
    ) -> Any:
        """
        Resolve um valor individual.
        """

        if isinstance(
            value,
            ResultReference,
        ):
            if value.step_id not in results:
                raise PlanExecutionError(
                    "Resultado da etapa "
                    f"{value.step_id!r} não está disponível."
                )

            return results[value.step_id]

        return value