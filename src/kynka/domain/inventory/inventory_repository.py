"""
Contrato de persistência do domínio de inventário.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .inventory_movement import InventoryMovement
from .material import Material


class InventoryRepository(ABC):
    """
    Define o contrato de persistência do inventário.

    O domínio não conhece SQLite, Excel, ERP ou qualquer
    outra tecnologia concreta de armazenamento.
    """

    @abstractmethod
    def save(
        self,
        material: Material,
    ) -> None:
        """
        Cria ou atualiza um material.
        """

    @abstractmethod
    def delete(
        self,
        code: str,
    ) -> bool:
        """
        Exclui um material.

        Retorna True quando o material existia.
        """

    @abstractmethod
    def get_by_code(
        self,
        code: str,
    ) -> Material | None:
        """
        Procura um material pelo código.
        """

    @abstractmethod
    def search(
        self,
        query: str,
    ) -> list[Material]:
        """
        Procura materiais pelo código ou nome.
        """

    @abstractmethod
    def list_all(
        self,
    ) -> list[Material]:
        """
        Retorna todos os materiais.
        """

    @abstractmethod
    def save_movement(
        self,
        movement: InventoryMovement,
    ) -> InventoryMovement:
        """
        Persiste uma movimentação.
        """

    @abstractmethod
    def apply_movement(
        self,
        material: Material,
        movement: InventoryMovement,
    ) -> InventoryMovement:
        """
        Atualiza o saldo e registra a movimentação
        na mesma transação.
        """

    @abstractmethod
    def list_movements(
        self,
        material_code: str | None = None,
        limit: int = 100,
    ) -> list[InventoryMovement]:
        """
        Lista o histórico de movimentações.
        """