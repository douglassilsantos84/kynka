"""
Plano de tarefas da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .plan_step import (
    PlanStep,
    ResultReference,
)


class TaskPlanValidationError(Exception):
    """
    Erro encontrado durante a validação
    estrutural de um plano.
    """


@dataclass(slots=True)
class TaskPlan:
    """
    Representa um plano composto por etapas ordenadas.

    Cada etapa pode utilizar resultados produzidos
    por etapas anteriores através de ResultReference.
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

        self.steps.append(
            step
        )

    def validate(self) -> None:
        """
        Valida a estrutura completa do plano.

        Regras:

        - IDs não podem estar vazios;
        - IDs precisam ser únicos;
        - Capability não pode estar vazia;
        - referências precisam apontar para etapas existentes;
        - uma etapa somente pode depender de etapas anteriores;
        - referências circulares ou futuras não são permitidas.
        """

        known_steps: set[str] = set()

        for step in self.steps:
            step_id = step.id.strip()

            if not step_id:
                raise TaskPlanValidationError(
                    "Uma etapa do plano possui "
                    "ID vazio."
                )

            if step_id in known_steps:
                raise TaskPlanValidationError(
                    "ID de etapa duplicado: "
                    f"{step_id!r}."
                )

            capability = (
                step.capability.strip()
            )

            if not capability:
                raise TaskPlanValidationError(
                    "A etapa "
                    f"{step_id!r} não possui "
                    "uma Capability válida."
                )

            self._validate_references(
                step=step,
                known_steps=known_steps,
            )

            known_steps.add(
                step_id
            )

    def _validate_references(
        self,
        step: PlanStep,
        known_steps: set[str],
    ) -> None:
        """
        Valida as referências utilizadas
        nos argumentos de uma etapa.
        """

        for argument_name, value in (
            step.arguments.items()
        ):
            self._validate_value_reference(
                step=step,
                argument_name=argument_name,
                value=value,
                known_steps=known_steps,
            )

    def _validate_value_reference(
        self,
        step: PlanStep,
        argument_name: str,
        value: object,
        known_steps: set[str],
    ) -> None:
        """
        Valida recursivamente referências encontradas
        dentro de um argumento.
        """

        if isinstance(
            value,
            ResultReference,
        ):
            referenced_step = (
                value.step_id.strip()
            )

            if not referenced_step:
                raise TaskPlanValidationError(
                    "A etapa "
                    f"{step.id!r} possui uma referência "
                    f"vazia no argumento {argument_name!r}."
                )

            if referenced_step not in known_steps:
                raise TaskPlanValidationError(
                    "A etapa "
                    f"{step.id!r} referencia "
                    f"{referenced_step!r} no argumento "
                    f"{argument_name!r}, mas essa etapa "
                    "não existe anteriormente no plano."
                )

            return

        if isinstance(
            value,
            dict,
        ):
            for nested_value in value.values():
                self._validate_value_reference(
                    step=step,
                    argument_name=argument_name,
                    value=nested_value,
                    known_steps=known_steps,
                )

            return

        if isinstance(
            value,
            (list, tuple),
        ):
            for nested_value in value:
                self._validate_value_reference(
                    step=step,
                    argument_name=argument_name,
                    value=nested_value,
                    known_steps=known_steps,
                )

    def __len__(self) -> int:
        """
        Retorna a quantidade de etapas.
        """

        return len(
            self.steps
        )

    def __iter__(self):
        """
        Permite iterar diretamente sobre o plano.
        """

        return iter(
            self.steps
        )