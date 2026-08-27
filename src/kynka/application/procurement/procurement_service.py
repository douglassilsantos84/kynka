"""Serviço de compras e consolidação de necessidades da Kynka."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from kynka.application.demand import DemandNotFoundError
from kynka.domain.demand import DemandRepository
from kynka.domain.inventory import InventoryRepository


@dataclass(slots=True)
class PurchaseDemandShare:
    demand_id: int
    demand_code: str
    demand_name: str
    required_quantity: float
    reserved_quantity: float
    remaining_quantity: float


@dataclass(slots=True)
class PurchaseListItem:
    material_code: str
    material_name: str
    unit: str
    required_quantity: float
    reserved_quantity: float
    physical_quantity: float
    minimum_quantity: float
    reserved_total: float
    free_quantity: float
    quantity_to_buy: float
    demands: list[PurchaseDemandShare] = field(default_factory=list)


@dataclass(slots=True)
class PurchaseList:
    demand_ids: list[int]
    demand_codes: list[str]
    total_materials: int
    materials_to_buy: int
    items: list[PurchaseListItem]
    analysis: str


class ProcurementService:
    def __init__(self, demand_repository: DemandRepository, inventory_repository: InventoryRepository) -> None:
        self._demand_repository = demand_repository
        self._inventory_repository = inventory_repository

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        if not value:
            return ""
        value = value.strip().lower()
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(c for c in normalized if not unicodedata.combining(c))

    def for_demand(self, demand_id: int) -> PurchaseList:
        demand = self._demand_repository.get_demand(int(demand_id))
        if demand is None:
            raise DemandNotFoundError(f"Demanda não encontrada: {demand_id}.")
        return self.consolidated([demand.id])

    def consolidated(self, demand_ids: list[int] | None = None) -> PurchaseList:
        if demand_ids is None:
            demands = self._demand_repository.list_demands()
        else:
            seen = set()
            demands = []
            for value in demand_ids:
                demand_id = int(value)
                if demand_id in seen:
                    continue
                seen.add(demand_id)
                demand = self._demand_repository.get_demand(demand_id)
                if demand is None:
                    raise DemandNotFoundError(f"Demanda não encontrada: {demand_id}.")
                demands.append(demand)

        aggregate = {}
        for demand in demands:
            requirements = self._demand_repository.list_requirements(demand.id)
            for requirement in requirements:
                material = self._inventory_repository.get_by_code(requirement.material_code)
                if material is None:
                    continue
                reservation = self._demand_repository.get_reservation(demand.id, material.code)
                reserved_for_demand = reservation.quantity if reservation else 0.0
                remaining = max(requirement.required_quantity - reserved_for_demand, 0.0)
                entry = aggregate.setdefault(material.code, {
                    "material": material,
                    "required": 0.0,
                    "reserved": 0.0,
                    "remaining": 0.0,
                    "demands": [],
                })
                entry["required"] += requirement.required_quantity
                entry["reserved"] += reserved_for_demand
                entry["remaining"] += remaining
                entry["demands"].append(PurchaseDemandShare(
                    demand_id=demand.id,
                    demand_code=demand.code,
                    demand_name=demand.name,
                    required_quantity=requirement.required_quantity,
                    reserved_quantity=reserved_for_demand,
                    remaining_quantity=remaining,
                ))

        items = []
        for code, entry in aggregate.items():
            material = entry["material"]
            reserved_total = self._demand_repository.total_reserved(code)
            free_quantity = max(material.quantity - material.minimum_quantity - reserved_total, 0.0)
            quantity_to_buy = max(entry["remaining"] - free_quantity, 0.0)
            if quantity_to_buy <= 0:
                continue
            items.append(PurchaseListItem(
                material_code=material.code,
                material_name=material.name,
                unit=material.unit,
                required_quantity=entry["required"],
                reserved_quantity=entry["reserved"],
                physical_quantity=material.quantity,
                minimum_quantity=material.minimum_quantity,
                reserved_total=reserved_total,
                free_quantity=free_quantity,
                quantity_to_buy=quantity_to_buy,
                demands=entry["demands"],
            ))

        items.sort(key=lambda item: (item.material_name.lower(), item.material_code.lower()))
        codes = [demand.code for demand in demands]
        analysis = self._analysis(codes, len(aggregate), items)
        return PurchaseList(
            demand_ids=[demand.id for demand in demands],
            demand_codes=codes,
            total_materials=len(aggregate),
            materials_to_buy=len(items),
            items=items,
            analysis=analysis,
        )

    def _find_demand_in_text(self, text: str, demands):
        normalized_text = self._normalize_text(text)
        for demand in demands:
            code = self._normalize_text(demand.code)
            if code and code in normalized_text:
                return demand
        for demand in demands:
            name = self._normalize_text(demand.name)
            if name and name in normalized_text:
                return demand
        candidates = []
        for demand in demands:
            name = self._normalize_text(demand.name)
            words = [word for word in name.split() if len(word) >= 3]
            if not words:
                continue
            matches = sum(1 for word in words if word in normalized_text)
            if matches >= 2 and matches == len(words):
                candidates.append(demand)
        return candidates[0] if len(candidates) == 1 else None

    def try_answer(self, text: str):
        normalized_text = self._normalize_text(text)
        purchase_terms = (
            "comprar", "compras", "falta comprar", "faltando",
            "materiais faltam", "materiais estao faltando", "material falta",
            "material faltando", "lista de compra", "lista de compras", "o que falta",
        )
        if not any(term in normalized_text for term in purchase_terms):
            return None
        demands = self._demand_repository.list_demands()
        consolidated_terms = (
            "todas as obras", "todos os projetos", "todas as demandas",
            "lista consolidada", "lista de compras consolidada", "compras consolidadas",
        )
        if any(term in normalized_text for term in consolidated_terms):
            purchase_list = self.consolidated()
            return purchase_list.analysis, purchase_list
        demand = self._find_demand_in_text(text, demands)
        if demand is not None:
            purchase_list = self.for_demand(demand.id)
            return purchase_list.analysis, purchase_list
        return None

    @staticmethod
    def _analysis(codes, total, items):
        if not codes:
            return "Não há projetos selecionados para calcular a lista de compras."
        scope = codes[0] if len(codes) == 1 else f"{len(codes)} projetos selecionados"
        if not items:
            return (
                f"{scope}: não há necessidade de compra com os dados atuais. "
                "O estoque mínimo e as reservas existentes foram preservados."
            )
        lines = [f"{scope}: {len(items)} de {total} material(is) precisam de compra."]
        for item in items[:8]:
            lines.append(
                f"{item.material_code} — {item.material_name}: comprar "
                f"{item.quantity_to_buy:g} {item.unit}."
            )
        if len(items) > 8:
            lines.append(f"Há mais {len(items) - 8} material(is) na lista.")
        lines.append("O cálculo preserva o estoque mínimo e desconta todas as reservas existentes.")
        return "\n".join(lines)
