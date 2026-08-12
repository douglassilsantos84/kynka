"""
Planejador híbrido da plataforma Kynka.
"""

from __future__ import annotations

from collections.abc import Mapping

from kynka.application.planning.llm_planner import (
    LLMPlanner,
)
from kynka.application.planning.planner import (
    DeterministicPlanner,
    PlanningError,
)
from kynka.application.planning.task_plan import (
    TaskPlan,
)


class HybridPlanner:
    """
    Combina planejamento determinístico
    e planejamento baseado em LLM.

    Estratégia:

    1. tenta criar o plano deterministicamente;
    2. se o planejador determinístico não compreender
       o objetivo, utiliza o LLM;
    3. valida se todas as Capabilities do plano
       estão disponíveis;
    4. se ambos falharem, lança PlanningError.
    """

    def __init__(
        self,
        deterministic_planner: DeterministicPlanner,
        llm_planner: LLMPlanner,
    ) -> None:
        self._deterministic_planner = (
            deterministic_planner
        )

        self._llm_planner = llm_planner

    def plan(
        self,
        goal: str,
        available_capabilities: Mapping[str, str],
    ) -> TaskPlan:
        """
        Cria um plano para atingir o objetivo informado.
        """

        goal = goal.strip()

        if not goal:
            raise PlanningError(
                "O objetivo não pode estar vazio."
            )

        # --------------------------------------------------
        # 1. Planejamento determinístico
        # --------------------------------------------------

        try:
            plan = self._deterministic_planner.plan(
                goal
            )

            self._validate_plan(
                plan=plan,
                available_capabilities=(
                    available_capabilities
                ),
            )

            return plan

        except PlanningError:
            pass

        # --------------------------------------------------
        # 2. Fallback para LLM
        # --------------------------------------------------

        try:
            plan = self._llm_planner.plan(
                goal,
                available_capabilities,
            )

            self._validate_plan(
                plan=plan,
                available_capabilities=(
                    available_capabilities
                ),
            )

            return plan

        except PlanningError as error:
            raise PlanningError(
                "Nenhum planejador conseguiu criar "
                f"um plano para o objetivo: {goal!r}"
            ) from error

    @staticmethod
    def _validate_plan(
        plan: TaskPlan,
        available_capabilities: Mapping[str, str],
    ) -> None:
        """
        Valida se o plano produzido pode ser executado
        com as Capabilities atualmente disponíveis.
        """

        if len(plan) == 0:
            raise PlanningError(
                "O planejador produziu um plano vazio."
            )

        for step in plan.steps:
            if step.capability not in available_capabilities:
                raise PlanningError(
                    "O plano utiliza uma Capability "
                    "que não está disponível: "
                    f"{step.capability!r}"
                )