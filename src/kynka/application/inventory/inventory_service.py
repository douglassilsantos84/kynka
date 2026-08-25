"""
Serviço de aplicação para gerenciamento de inventário da Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass

from kynka.domain.inventory import (
    InventoryMovement,
    InventoryRepository,
    Material,
    MovementType,
)


class MaterialNotFoundError(Exception):
    """
    Material não encontrado no inventário.
    """


class MaterialAlreadyExistsError(Exception):
    """
    Tentativa de criar um código que já existe.
    """


class InsufficientStockError(Exception):
    """
    Tentativa de retirar quantidade superior ao saldo.
    """


@dataclass(slots=True)
class InventorySummary:
    """
    Resumo geral do inventário.
    """

    total_materials: int
    below_minimum: int
    zero_stock: int


@dataclass(slots=True)
class ReplenishmentItem:
    """
    Representa uma necessidade de reposição de estoque.
    """

    code: str
    name: str
    current_quantity: float
    minimum_quantity: float
    quantity_to_buy: float
    unit: str


class InventoryService:
    """
    Coordena as regras de negócio do inventário.
    """

    def __init__(
        self,
        repository: InventoryRepository,
    ) -> None:
        self._repository = repository

    # ========================================================
    # Material
    # ========================================================

    def create_material(
        self,
        code: str,
        name: str,
        quantity: float = 0.0,
        unit: str = "un",
        minimum_quantity: float = 0.0,
    ) -> Material:
        """
        Cria um material novo.
        """

        normalized_code = self._normalize_code(code)

        if self._repository.get_by_code(normalized_code):
            raise MaterialAlreadyExistsError(
                f"Já existe um material com o código "
                f"{normalized_code!r}."
            )

        material = self._build_material(
            code=normalized_code,
            name=name,
            quantity=quantity,
            unit=unit,
            minimum_quantity=minimum_quantity,
        )

        self._repository.save(material)

        return material

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

        Mantido para compatibilidade com o importador existente.
        """

        material = self._build_material(
            code=code,
            name=name,
            quantity=quantity,
            unit=unit,
            minimum_quantity=minimum_quantity,
        )

        self._repository.save(material)

        return material

    def update_material(
        self,
        code: str,
        name: str,
        unit: str = "un",
        minimum_quantity: float = 0.0,
    ) -> Material:
        """
        Edita os dados cadastrais sem alterar o saldo.
        """

        material = self.get_material(code)

        normalized_name = name.strip()
        normalized_unit = unit.strip() or "un"
        minimum_quantity = float(minimum_quantity)

        if not normalized_name:
            raise ValueError(
                "O nome do material não pode estar vazio."
            )

        if minimum_quantity < 0:
            raise ValueError(
                "A quantidade mínima não pode ser negativa."
            )

        material.name = normalized_name
        material.unit = normalized_unit
        material.minimum_quantity = minimum_quantity

        self._repository.save(material)

        return material

    def delete_material(
        self,
        code: str,
    ) -> None:
        """
        Exclui um material.
        """

        normalized_code = self._normalize_code(code)

        self.get_material(normalized_code)

        deleted = self._repository.delete(
            normalized_code
        )

        if not deleted:
            raise MaterialNotFoundError(
                f"Material não encontrado: "
                f"{normalized_code!r}."
            )

    def get_material(
        self,
        code: str,
    ) -> Material:
        """
        Retorna um material pelo código.
        """

        normalized_code = self._normalize_code(code)

        material = self._repository.get_by_code(
            normalized_code
        )

        if material is None:
            raise MaterialNotFoundError(
                f"Material não encontrado: "
                f"{normalized_code!r}."
            )

        return material

    def search_materials(
        self,
        query: str,
    ) -> list[Material]:
        normalized_query = query.strip()

        if not normalized_query:
            return []

        return self._repository.search(
            normalized_query
        )

    def list_materials(
        self,
    ) -> list[Material]:
        return self._repository.list_all()

    # ========================================================
    # Movements
    # ========================================================

    def add_entry(
        self,
        code: str,
        quantity: float,
        reason: str = "",
    ) -> InventoryMovement:
        """
        Registra entrada de estoque.
        """

        quantity = self._positive_quantity(quantity)

        material = self.get_material(code)

        previous = material.quantity
        new_quantity = previous + quantity

        movement = InventoryMovement(
            material_code=material.code,
            movement_type=MovementType.ENTRY,
            quantity=quantity,
            previous_quantity=previous,
            new_quantity=new_quantity,
            reason=reason.strip(),
        )

        material.quantity = new_quantity

        return self._repository.apply_movement(
            material,
            movement,
        )

    def add_exit(
        self,
        code: str,
        quantity: float,
        reason: str = "",
    ) -> InventoryMovement:
        """
        Registra saída de estoque.
        """

        quantity = self._positive_quantity(quantity)

        material = self.get_material(code)

        if quantity > material.quantity:
            raise InsufficientStockError(
                "Estoque insuficiente. "
                f"Saldo atual: {material.quantity:g} "
                f"{material.unit}."
            )

        previous = material.quantity
        new_quantity = previous - quantity

        movement = InventoryMovement(
            material_code=material.code,
            movement_type=MovementType.EXIT,
            quantity=quantity,
            previous_quantity=previous,
            new_quantity=new_quantity,
            reason=reason.strip(),
        )

        material.quantity = new_quantity

        return self._repository.apply_movement(
            material,
            movement,
        )

    def adjust_stock(
        self,
        code: str,
        new_quantity: float,
        reason: str = "",
    ) -> InventoryMovement:
        """
        Define manualmente o saldo de um material.
        """

        new_quantity = float(new_quantity)

        if new_quantity < 0:
            raise ValueError(
                "O novo saldo não pode ser negativo."
            )

        material = self.get_material(code)

        previous = material.quantity

        movement = InventoryMovement(
            material_code=material.code,
            movement_type=MovementType.ADJUSTMENT,
            quantity=abs(new_quantity - previous),
            previous_quantity=previous,
            new_quantity=new_quantity,
            reason=reason.strip(),
        )

        material.quantity = new_quantity

        return self._repository.apply_movement(
            material,
            movement,
        )

    def list_movements(
        self,
        material_code: str | None = None,
        limit: int = 100,
    ) -> list[InventoryMovement]:
        """
        Consulta o histórico.
        """

        limit = int(limit)

        if limit < 1:
            raise ValueError(
                "O limite deve ser maior que zero."
            )

        if limit > 1000:
            limit = 1000

        normalized_code = None

        if material_code:
            normalized_code = self._normalize_code(
                material_code
            )

            self.get_material(normalized_code)

        return self._repository.list_movements(
            material_code=normalized_code,
            limit=limit,
        )

    # ========================================================
    # Indicators
    # ========================================================

    def list_below_minimum(
        self,
    ) -> list[Material]:
        return [
            material
            for material in self._repository.list_all()
            if material.is_below_minimum
        ]

    def list_zero_stock(
        self,
    ) -> list[Material]:
        return [
            material
            for material in self._repository.list_all()
            if material.quantity <= 0
        ]

    def summary(
        self,
    ) -> InventorySummary:
        materials = self._repository.list_all()

        return InventorySummary(
            total_materials=len(materials),
            below_minimum=sum(
                1
                for material in materials
                if material.is_below_minimum
            ),
            zero_stock=sum(
                1
                for material in materials
                if material.quantity <= 0
            ),
        )

    # ========================================================
    # Replenishment
    # ========================================================

    def list_replenishment_needs(
        self,
    ) -> list[ReplenishmentItem]:
        """
        Retorna os materiais que precisam de reposição.

        A quantidade sugerida para compra corresponde à diferença
        entre o estoque mínimo e o saldo atual.
        """

        items: list[ReplenishmentItem] = []

        for material in self._repository.list_all():
            if not material.is_below_minimum:
                continue

            quantity_to_buy = max(
                material.minimum_quantity - material.quantity,
                0.0,
            )

            items.append(
                ReplenishmentItem(
                    code=material.code,
                    name=material.name,
                    current_quantity=material.quantity,
                    minimum_quantity=material.minimum_quantity,
                    quantity_to_buy=quantity_to_buy,
                    unit=material.unit,
                )
            )

        return sorted(
            items,
            key=lambda item: (
                item.name.lower(),
                item.code.lower(),
            ),
        )

    # ========================================================
    # Validation
    # ========================================================

    @staticmethod
    def _normalize_code(
        code: str,
    ) -> str:
        normalized = code.strip()

        if not normalized:
            raise ValueError(
                "O código do material não pode estar vazio."
            )

        return normalized

    @classmethod
    def _build_material(
        cls,
        code: str,
        name: str,
        quantity: float,
        unit: str,
        minimum_quantity: float,
    ) -> Material:
        normalized_code = cls._normalize_code(code)
        normalized_name = name.strip()
        normalized_unit = unit.strip() or "un"

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

        return Material(
            code=normalized_code,
            name=normalized_name,
            quantity=quantity,
            unit=normalized_unit,
            minimum_quantity=minimum_quantity,
        )

    @staticmethod
    def _positive_quantity(
        quantity: float,
    ) -> float:
        quantity = float(quantity)

        if quantity <= 0:
            raise ValueError(
                "A quantidade deve ser maior que zero."
            )

        return quantity