"""
ServiÃ§o de planejamento de demandas da Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from kynka.domain.demand import (
    Demand,
    DemandRepository,
    DemandRequirement,
    DemandStatus,
    StockReservation,
)
from kynka.domain.inventory import (
    InventoryRepository,
)


class DemandNotFoundError(Exception):
    """
    Demanda nÃ£o encontrada.
    """


class DemandAlreadyExistsError(Exception):
    """
    CÃ³digo de demanda jÃ¡ existente.
    """


class DemandMaterialNotFoundError(Exception):
    """
    Material da demanda nÃ£o existe no estoque.
    """


@dataclass(slots=True)
class DemandPlanItem:
    """
    Resultado do planejamento de um material.
    """

    material_code: str
    material_name: str
    unit: str

    required_quantity: float

    physical_quantity: float
    minimum_quantity: float

    reserved_total: float
    reserved_for_this_demand: float
    reserved_for_other_demands: float

    free_quantity: float

    quantity_still_required: float
    quantity_available_to_reserve: float

    shortage_quantity: float

    fully_available: bool


@dataclass(slots=True)
class DemandPlan:
    """
    Resultado completo do planejamento de uma demanda.
    """

    demand_id: int
    demand_code: str
    demand_name: str

    total_items: int
    available_items: int
    shortage_items: int

    items: list[DemandPlanItem]


class DemandService:
    """
    Coordena demandas, necessidades e reservas de estoque.
    """

    def __init__(
        self,
        repository: DemandRepository,
        inventory_repository: InventoryRepository,
    ) -> None:
        self._repository = repository
        self._inventory_repository = inventory_repository

    # ========================================================
    # Demand
    # ========================================================

    def create_demand(
        self,
        code: str,
        name: str,
        kind: str = "project",
        client: str = "",
        location: str = "",
        start_date: date | None = None,
        notes: str = "",
    ) -> Demand:
        """
        Cria uma nova demanda.
        """

        normalized_code = code.strip()
        normalized_name = name.strip()
        normalized_kind = kind.strip() or "project"

        if not normalized_code:
            raise ValueError(
                "O cÃ³digo da demanda nÃ£o pode estar vazio."
            )

        if not normalized_name:
            raise ValueError(
                "O nome da demanda nÃ£o pode estar vazio."
            )

        if self._repository.get_demand_by_code(
            normalized_code
        ):
            raise DemandAlreadyExistsError(
                f"JÃ¡ existe uma demanda com o cÃ³digo "
                f"{normalized_code!r}."
            )

        demand = Demand(
            code=normalized_code,
            name=normalized_name,
            kind=normalized_kind,
            client=client.strip(),
            location=location.strip(),
            start_date=start_date,
            status=DemandStatus.DRAFT,
            notes=notes.strip(),
        )

        return self._repository.save_demand(
            demand
        )

    def get_demand(
        self,
        demand_id: int,
    ) -> Demand:
        demand = self._repository.get_demand(
            int(demand_id)
        )

        if demand is None:
            raise DemandNotFoundError(
                f"Demanda nÃ£o encontrada: {demand_id}."
            )

        return demand

    def list_demands(
        self,
    ) -> list[Demand]:
        return self._repository.list_demands()

    # ========================================================
    # Requirements
    # ========================================================

    def set_requirement(
        self,
        demand_id: int,
        material_code: str,
        required_quantity: float,
    ) -> DemandRequirement:
        """
        Define quanto de um material a demanda necessita.
        """

        demand = self.get_demand(
            demand_id
        )

        material_code = material_code.strip()

        material = self._inventory_repository.get_by_code(
            material_code
        )

        if material is None:
            raise DemandMaterialNotFoundError(
                f"Material nÃ£o encontrado no estoque: "
                f"{material_code!r}."
            )

        required_quantity = float(
            required_quantity
        )

        if required_quantity <= 0:
            raise ValueError(
                "A quantidade necessÃ¡ria deve ser "
                "maior que zero."
            )

        requirement = DemandRequirement(
            demand_id=demand.id,
            material_code=material.code,
            required_quantity=required_quantity,
        )

        return self._repository.save_requirement(
            requirement
        )

    def list_requirements(
        self,
        demand_id: int,
    ) -> list[DemandRequirement]:
        self.get_demand(demand_id)

        return self._repository.list_requirements(
            demand_id
        )


    def remove_requirement(
        self,
        demand_id: int,
        material_code: str,
    ) -> bool:
        """
        Remove a necessidade de um material da demanda.
        """

        self.get_demand(demand_id)

        normalized_code = material_code.strip()

        if not normalized_code:
            raise ValueError(
                "O código do material não pode estar vazio."
            )

        return self._repository.delete_requirement(
            demand_id,
            normalized_code,
        )

    # ========================================================
    # Planning
    # ========================================================

    def calculate_plan(
        self,
        demand_id: int,
    ) -> DemandPlan:
        """
        Cruza a necessidade da demanda com:

        - estoque fÃ­sico;
        - estoque mÃ­nimo;
        - reservas existentes;
        - reservas da prÃ³pria demanda.

        O estoque mÃ­nimo permanece protegido.
        """

        demand = self.get_demand(
            demand_id
        )

        requirements = (
            self._repository.list_requirements(
                demand.id
            )
        )

        items: list[DemandPlanItem] = []

        available_items = 0
        shortage_items = 0

        for requirement in requirements:

            material = (
                self._inventory_repository
                .get_by_code(
                    requirement.material_code
                )
            )

            if material is None:
                raise DemandMaterialNotFoundError(
                    f"Material nÃ£o encontrado no estoque: "
                    f"{requirement.material_code!r}."
                )

            own_reservation = (
                self._repository.get_reservation(
                    demand.id,
                    material.code,
                )
            )

            reserved_for_this = (
                own_reservation.quantity
                if own_reservation
                else 0.0
            )

            reserved_total = (
                self._repository.total_reserved(
                    material.code
                )
            )

            reserved_other = max(
                reserved_total
                - reserved_for_this,
                0.0,
            )

            # ------------------------------------------------
            # Estoque livre real.
            #
            # O estoque mÃ­nimo Ã© protegido e nÃ£o pode ser
            # prometido para uma nova demanda.
            # ------------------------------------------------

            free_quantity = max(
                material.quantity
                - material.minimum_quantity
                - reserved_total,
                0.0,
            )

            quantity_still_required = max(
                requirement.required_quantity
                - reserved_for_this,
                0.0,
            )

            quantity_available_to_reserve = min(
                quantity_still_required,
                free_quantity,
            )

            shortage_quantity = max(
                quantity_still_required
                - quantity_available_to_reserve,
                0.0,
            )

            fully_available = (
                shortage_quantity <= 0
            )

            if fully_available:
                available_items += 1
            else:
                shortage_items += 1

            items.append(
                DemandPlanItem(
                    material_code=material.code,
                    material_name=material.name,
                    unit=material.unit,

                    required_quantity=(
                        requirement.required_quantity
                    ),

                    physical_quantity=(
                        material.quantity
                    ),

                    minimum_quantity=(
                        material.minimum_quantity
                    ),

                    reserved_total=reserved_total,

                    reserved_for_this_demand=(
                        reserved_for_this
                    ),

                    reserved_for_other_demands=(
                        reserved_other
                    ),

                    free_quantity=free_quantity,

                    quantity_still_required=(
                        quantity_still_required
                    ),

                    quantity_available_to_reserve=(
                        quantity_available_to_reserve
                    ),

                    shortage_quantity=(
                        shortage_quantity
                    ),

                    fully_available=fully_available,
                )
            )

        return DemandPlan(
            demand_id=demand.id,
            demand_code=demand.code,
            demand_name=demand.name,
            total_items=len(items),
            available_items=available_items,
            shortage_items=shortage_items,
            items=items,
        )

    # ========================================================
    # Reservations
    # ========================================================

    def reserve_available_stock(
        self,
        demand_id: int,
    ) -> DemandPlan:
        """
        Reserva automaticamente o mÃ¡ximo possÃ­vel para a
        demanda, sem consumir o estoque mÃ­nimo.
        """

        plan = self.calculate_plan(
            demand_id
        )

        for item in plan.items:

            if item.quantity_available_to_reserve <= 0:
                continue

            new_reserved_quantity = (
                item.reserved_for_this_demand
                + item.quantity_available_to_reserve
            )

            reservation = StockReservation(
                demand_id=demand_id,
                material_code=item.material_code,
                quantity=new_reserved_quantity,
            )

            self._repository.set_reservation(
                reservation
            )

        return self.calculate_plan(
            demand_id
        )

    def list_reservations(
        self,
        demand_id: int,
    ) -> list[StockReservation]:
        self.get_demand(
            demand_id
        )

        return self._repository.list_reservations(
            demand_id
        )
