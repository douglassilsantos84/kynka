"""
Contrato de persistência do domínio de inventário.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .material import Material


class InventoryRepository(ABC):
    """
    Define as operações de persistência necessárias
    para o inventário.

    O domínio não conhece SQLite, Excel, ERP
    ou qualquer outra tecnologia de armazenamento.
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