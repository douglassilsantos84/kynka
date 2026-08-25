"""
Caso de uso para resolver materiais do mapa de quantidades
que ainda não existem no estoque.
"""

from __future__ import annotations

from dataclasses import dataclass

from kynka.application.inventory import InventoryService
from kynka.domain.demand import DemandRequirement
from kynka.domain.inventory import Material

from .demand_service import DemandPlan, DemandService


class MissingMaterialResolutionError(Exception):
    """
    Falha ao resolver ou desfazer a resolução de um material pendente.
    """


@dataclass(slots=True)
class ResolveMissingMaterialResult:
    """
    Resultado da resolução de um material pendente.
    """

    material: Material
    requirement: DemandRequirement
    plan: DemandPlan


class MissingMaterialService:
    """
    Coordena cadastro do material, inclusão no projeto e recálculo.

    A arquitetura atual usa operações SQLite separadas. Por isso,
    enquanto não houver uma Unit of Work compartilhada, este caso de
    uso aplica compensação: se uma etapa posterior falhar, desfaz as
    alterações já concluídas.
    """

    def __init__(
        self,
        inventory_service: InventoryService,
        demand_service: DemandService,
    ) -> None:
        self._inventory_service = inventory_service
        self._demand_service = demand_service

    def resolve(
        self,
        *,
        demand_id: int,
        code: str,
        name: str,
        quantity: float = 0.0,
        unit: str = "un",
        minimum_quantity: float = 0.0,
        required_quantity: float,
    ) -> ResolveMissingMaterialResult:
        """
        Cadastra um material inexistente e o adiciona à demanda.
        """

        # Valida a demanda antes de alterar o estoque.
        self._demand_service.get_demand(demand_id)

        normalized_code = code.strip()
        normalized_name = name.strip()
        normalized_unit = unit.strip() or "un"

        quantity = float(quantity)
        minimum_quantity = float(minimum_quantity)
        required_quantity = float(required_quantity)

        if not normalized_code:
            raise ValueError(
                "O código do material não pode estar vazio."
            )

        if not normalized_name:
            raise ValueError(
                "O nome do material não pode estar vazio."
            )

        if quantity < 0:
            raise ValueError(
                "O estoque físico não pode ser negativo."
            )

        if minimum_quantity < 0:
            raise ValueError(
                "O estoque mínimo não pode ser negativo."
            )

        if required_quantity <= 0:
            raise ValueError(
                "A necessidade do projeto deve ser maior que zero."
            )

        material_created = False
        requirement_created = False

        try:
            material = self._inventory_service.create_material(
                code=normalized_code,
                name=normalized_name,
                quantity=quantity,
                unit=normalized_unit,
                minimum_quantity=minimum_quantity,
            )
            material_created = True

            requirement = self._demand_service.set_requirement(
                demand_id=demand_id,
                material_code=material.code,
                required_quantity=required_quantity,
            )
            requirement_created = True

            plan = self._demand_service.calculate_plan(
                demand_id
            )

            return ResolveMissingMaterialResult(
                material=material,
                requirement=requirement,
                plan=plan,
            )

        except Exception as error:
            rollback_errors: list[str] = []

            if requirement_created:
                try:
                    self._demand_service.remove_requirement(
                        demand_id=demand_id,
                        material_code=normalized_code,
                    )
                except Exception as rollback_error:
                    rollback_errors.append(
                        f"requisito: {rollback_error}"
                    )

            if material_created:
                try:
                    self._inventory_service.delete_material(
                        normalized_code
                    )
                except Exception as rollback_error:
                    rollback_errors.append(
                        f"material: {rollback_error}"
                    )

            if rollback_errors:
                raise MissingMaterialResolutionError(
                    "A operação falhou e a compensação não foi "
                    "concluída integralmente. "
                    f"Erro original: {error}. "
                    "Falhas ao desfazer: "
                    + "; ".join(rollback_errors)
                ) from error

            raise
