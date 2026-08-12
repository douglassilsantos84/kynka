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
    TaskPlanValidationError,
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

    Antes da execução, o plano é validado
    estruturalmente e todas as Capabilities são
    verificadas.
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
        Valida e executa todas as etapas de um plano
        na ordem em que foram definidas.
        """

        # --------------------------------------------------
        # Plano vazio
        # --------------------------------------------------

        if len(plan) == 0:
            return PlanExecutionResult(
                success=False,
                error="O plano não possui etapas.",
            )

        # --------------------------------------------------
        # Validação estrutural
        # --------------------------------------------------

        try:
            plan.validate()

        except TaskPlanValidationError as error:
            return PlanExecutionResult(
                success=False,
                error=(
                    "Plano inválido: "
                    f"{error}"
                ),
            )

        # --------------------------------------------------
        # Validação das Capabilities
        # --------------------------------------------------

        capability_error = (
            self._validate_capabilities(
                plan
            )
        )

        if capability_error is not None:
            return PlanExecutionResult(
                success=False,
                error=capability_error,
            )

        # --------------------------------------------------
        # Execução
        # --------------------------------------------------

        results: dict[str, Any] = {}
        executions: list[PlanStepExecution] = []

        for step in plan:
            # --------------------------------------------------
            # Resolução dos argumentos
            # --------------------------------------------------

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

                executions.append(
                    execution
                )

                return PlanExecutionResult(
                    success=False,
                    steps=executions,
                    error=str(error),
                )

            # --------------------------------------------------
            # Execução da Capability
            # --------------------------------------------------

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

                executions.append(
                    execution
                )

                return PlanExecutionResult(
                    success=False,
                    steps=executions,
                    error=str(error),
                )

            # --------------------------------------------------
            # CapabilityResult
            # --------------------------------------------------

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

                executions.append(
                    execution
                )

                if not capability_result.success:
                    return PlanExecutionResult(
                        success=False,
                        steps=executions,
                        error=capability_result.error,
                    )

                result_value = (
                    capability_result.data
                )

            # --------------------------------------------------
            # Resultado direto
            # --------------------------------------------------

            else:
                execution = PlanStepExecution(
                    step_id=step.id,
                    capability=step.capability,
                    arguments=arguments,
                    success=True,
                    result=capability_result,
                )

                executions.append(
                    execution
                )

                result_value = (
                    capability_result
                )

            # --------------------------------------------------
            # Registra resultado da etapa
            # --------------------------------------------------

            results[step.id] = result_value

        # --------------------------------------------------
        # Resultado final
        # --------------------------------------------------

        final_result = (
            executions[-1].result
        )

        return PlanExecutionResult(
            success=True,
            steps=executions,
            result=final_result,
        )

    def _validate_capabilities(
        self,
        plan: TaskPlan,
    ) -> str | None:
        """
        Verifica se todas as Capabilities utilizadas
        pelo plano estão registradas no Runtime.

        A validação ocorre antes da execução de
        qualquer etapa.
        """

        available_capabilities = (
            self._runtime.registry.capabilities
        )

        for step in plan:
            if (
                step.capability
                not in available_capabilities
            ):
                return (
                    "Capability não disponível "
                    "para execução: "
                    f"{step.capability!r} "
                    f"(etapa {step.id!r})."
                )

        return None

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

        Também suporta estruturas aninhadas,
        preparando o executor para Capabilities
        mais complexas.
        """

        # --------------------------------------------------
        # Referência a resultado anterior
        # --------------------------------------------------

        if isinstance(
            value,
            ResultReference,
        ):
            if value.step_id not in results:
                raise PlanExecutionError(
                    "Resultado da etapa "
                    f"{value.step_id!r} "
                    "não está disponível."
                )

            return results[
                value.step_id
            ]

        # --------------------------------------------------
        # Dicionário
        # --------------------------------------------------

        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._resolve_value(
                    value=nested_value,
                    results=results,
                )
                for key, nested_value
                in value.items()
            }

        # --------------------------------------------------
        # Lista
        # --------------------------------------------------

        if isinstance(
            value,
            list,
        ):
            return [
                self._resolve_value(
                    value=item,
                    results=results,
                )
                for item in value
            ]

        # --------------------------------------------------
        # Tupla
        # --------------------------------------------------

        if isinstance(
            value,
            tuple,
        ):
            return tuple(
                self._resolve_value(
                    value=item,
                    results=results,
                )
                for item in value
            )

        # --------------------------------------------------
        # Valor comum
        # --------------------------------------------------

        return value