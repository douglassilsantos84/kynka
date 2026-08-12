"""
Plano de execução de tarefas da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .plan_step import PlanStep


@dataclass(slots=True)
class TaskPlan:
    """
    Representa um plano composto por múltiplas etapas.

    O plano descreve uma sequência de Capabilities
    que poderão ser executadas pela plataforma.
    """

    steps: list[PlanStep] = field(
        default_factory=list
    )

    def add_step(
        self,
        step: PlanStep,
    ) -> None:
        """
        Adiciona uma etapa ao plano.
        """

        if any(
            existing_step.id == step.id
            for existing_step in self.steps
        ):
            raise ValueError(
                "Já existe uma etapa com o identificador "
                f"{step.id!r}."
            )

        self.steps.append(step)

    def get_step(
        self,
        step_id: str,
    ) -> PlanStep:
        """
        Localiza uma etapa pelo identificador.
        """

        for step in self.steps:
            if step.id == step_id:
                return step

        raise KeyError(
            f"Etapa não encontrada: {step_id!r}."
        )

    def __len__(self) -> int:
        return len(self.steps)

    def __iter__(self):
        return iter(self.steps)