"""
Serviço de aplicação para gerenciamento de inventário da Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass

from kynka.domain.inventory import (
    InventoryRepository,
    Material,
)


class MaterialNotFoundError(Exception):
    """
    Material não encontrado no inventário.
    """


@dataclass(slots=True)
class InventorySummary:
    """
    Resumo geral do inventário.
    """

    total_materials: int
    below_minimum: int
    zero_stock: int


class InventoryService:
    """
    Coordena as operações de negócio relacionadas
    ao inventário.
    """

    def __init__(
        self,
        repository: InventoryRepository,
    ) -> None:
        self._repository = repository

    def save_material(
        self,
        code: str,
        name: str,
        quantity: float,
        unit: str = "un",
        minimum_quantity: float = 0.0,
    ) -> Material:
        """
        Cria ou atualiza um material.
        """

        normalized_code = code.strip()
        normalized_name = name.strip()
        normalized_unit = unit.strip() or "un"

        if not normalized_code:
            raise ValueError(
                "O código do material não pode estar vazio."
            )

        if not normalized_name:
            raise ValueError(
                "O nome do material não pode estar vazio."
            )

        quantity = float(quantity)
        minimum_quantity = float(minimum_quantity)

        if quantity < 0:
            raise ValueError(
                "A quantidade não pode ser negativa."
            )

        if minimum_quantity < 0:
            raise ValueError(
                "A quantidade mínima não pode ser negativa."
            )

        material = Material(
            code=normalized_code,
            name=normalized_name,
            quantity=quantity,
            unit=normalized_unit,
            minimum_quantity=minimum_quantity,
        )

        self._repository.save(material)

        return material

    def get_material(
        self,
        code: str,
    ) -> Material:
        """
        Retorna um material pelo código.
        """

        material = self._repository.get_by_code(
            code.strip()
        )

        if material is None:
            raise MaterialNotFoundError(
                f"Material não encontrado: {code!r}."
            )

        return material

    def search_materials(
        self,
        query: str,
    ) -> list[Material]:
        """
        Pesquisa materiais pelo código ou nome.
        """

        normalized_query = query.strip()

        if not normalized_query:
            return []

        return self._repository.search(
            normalized_query
        )

    def list_materials(
        self,
    ) -> list[Material]:
        """
        Lista todos os materiais.
        """

        return self._repository.list_all()

    def list_below_minimum(
        self,
    ) -> list[Material]:
        """
        Retorna materiais cujo stock está
        abaixo da quantidade mínima.
        """

        return [
            material
            for material in self._repository.list_all()
            if material.is_below_minimum
        ]

    def list_zero_stock(
        self,
    ) -> list[Material]:
        """
        Retorna materiais sem stock.
        """

        return [
            material
            for material in self._repository.list_all()
            if material.quantity <= 0
        ]

    def summary(
        self,
    ) -> InventorySummary:
        """
        Retorna indicadores gerais do inventário.
        """

        materials = self._repository.list_all()

        below_minimum = sum(
            1
            for material in materials
            if material.is_below_minimum
        )

        zero_stock = sum(
            1
            for material in materials
            if material.quantity <= 0
        )

        return InventorySummary(
            total_materials=len(materials),
            below_minimum=below_minimum,
            zero_stock=zero_stock,
        )