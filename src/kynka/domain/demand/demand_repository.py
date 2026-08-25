"""
Contrato de persistência para planejamento de demandas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import (
    Demand,
    DemandRequirement,
    StockReservation,
)


class DemandRepository(ABC):
    """
    Contrato de persistência do módulo de demandas.
    """

    # ========================================================
    # Demand
    # ========================================================

    @abstractmethod
    def save_demand(
        self,
        demand: Demand,
    ) -> Demand:
        """
        Cria ou atualiza uma demanda.
        """

    @abstractmethod
    def get_demand(
        self,
        demand_id: int,
    ) -> Demand | None:
        """
        Consulta uma demanda pelo ID.
        """

    @abstractmethod
    def get_demand_by_code(
        self,
        code: str,
    ) -> Demand | None:
        """
        Consulta uma demanda pelo código.
        """

    @abstractmethod
    def list_demands(
        self,
    ) -> list[Demand]:
        """
        Lista todas as demandas.
        """

    @abstractmethod
    def delete_demand(
        self,
        demand_id: int,
    ) -> bool:
        """
        Exclui uma demanda.
        """

    # ========================================================
    # Requirements
    # ========================================================

    @abstractmethod
    def save_requirement(
        self,
        requirement: DemandRequirement,
    ) -> DemandRequirement:
        """
        Cria ou atualiza uma necessidade de material.
        """

    @abstractmethod
    def list_requirements(
        self,
        demand_id: int,
    ) -> list[DemandRequirement]:
        """
        Lista os materiais necessários para a demanda.
        """

    @abstractmethod
    def delete_requirement(
        self,
        demand_id: int,
        material_code: str,
    ) -> bool:
        """
        Remove um material da demanda.
        """

    # ========================================================
    # Reservations
    # ========================================================

    @abstractmethod
    def set_reservation(
        self,
        reservation: StockReservation,
    ) -> StockReservation:
        """
        Define a reserva de um material para uma demanda.
        """

    @abstractmethod
    def get_reservation(
        self,
        demand_id: int,
        material_code: str,
    ) -> StockReservation | None:
        """
        Consulta a reserva da demanda para um material.
        """

    @abstractmethod
    def list_reservations(
        self,
        demand_id: int,
    ) -> list[StockReservation]:
        """
        Lista reservas de uma demanda.
        """

    @abstractmethod
    def total_reserved(
        self,
        material_code: str,
    ) -> float:
        """
        Quantidade total reservada do material.
        """

    @abstractmethod
    def clear_reservations(
        self,
        demand_id: int,
    ) -> None:
        """
        Remove todas as reservas de uma demanda.
        """