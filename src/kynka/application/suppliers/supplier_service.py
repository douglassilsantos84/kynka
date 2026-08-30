"""Casos de uso de fornecedores, preços e inteligência de compras."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kynka.application.inventory import InventoryService, MaterialNotFoundError
from kynka.domain.demand import DemandRepository
from kynka.infrastructure.suppliers import SQLiteSupplierRepository

if TYPE_CHECKING:
    from kynka.application.procurement.procurement_service import ProcurementService


class SupplierNotFoundError(Exception):
    pass


class SupplierAlreadyExistsError(Exception):
    pass


class SupplierCatalogError(Exception):
    pass


@dataclass(slots=True)
class Supplier:
    id: int
    code: str
    name: str
    nif: str
    email: str
    phone: str
    notes: str
    active: bool
    created_at: str
    updated_at: str


@dataclass(slots=True)
class SupplierMaterial:
    id: int
    supplier_id: int
    material_code: str
    material_name: str
    unit: str
    unit_price: float
    lead_time_days: int
    minimum_order_quantity: float
    updated_at: str


@dataclass(slots=True)
class MaterialQuote:
    supplier_id: int
    supplier_code: str
    supplier_name: str
    material_code: str
    material_name: str
    unit: str
    requested_quantity: float
    order_quantity: float
    unit_price: float
    total_price: float
    lead_time_days: int
    minimum_order_quantity: float


@dataclass(slots=True)
class PurchaseSupplierOption:
    supplier_id: int
    supplier_code: str
    supplier_name: str
    covered_materials: int
    total_materials: int
    full_coverage: bool
    total_estimated: float
    max_lead_time_days: int
    items: list[MaterialQuote] = field(default_factory=list)


@dataclass(slots=True)
class PurchaseQuoteAnalysis:
    demand_ids: list[int]
    demand_codes: list[str]
    total_materials: int
    options: list[PurchaseSupplierOption]
    best_supplier_id: int | None
    best_supplier_name: str | None
    best_total_estimated: float | None
    best_mix_total: float | None
    best_mix: list[MaterialQuote]
    analysis: str


class SupplierService:
    def __init__(
        self,
        repository: SQLiteSupplierRepository,
        inventory_service: InventoryService,
        procurement_service: "ProcurementService",
        demand_repository: DemandRepository,
    ) -> None:
        self._repository = repository
        self._inventory_service = inventory_service
        self._procurement_service = procurement_service
        self._demand_repository = demand_repository

    @staticmethod
    def _normalize_code(value: str, label: str = "código") -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"O {label} não pode estar vazio.")
        return normalized

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKD", value.strip().lower())
        return "".join(c for c in normalized if not unicodedata.combining(c))

    @staticmethod
    def _supplier_from_record(record) -> Supplier:
        return Supplier(
            id=record.id,
            code=record.code,
            name=record.name,
            nif=record.nif,
            email=record.email,
            phone=record.phone,
            notes=record.notes,
            active=record.active,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def create_supplier(
        self,
        code: str,
        name: str,
        nif: str = "",
        email: str = "",
        phone: str = "",
        notes: str = "",
    ) -> Supplier:
        code = self._normalize_code(code, "código do fornecedor")
        name = name.strip()
        if not name:
            raise ValueError("O nome do fornecedor não pode estar vazio.")
        if self._repository.get_supplier_by_code(code):
            raise SupplierAlreadyExistsError(
                f"Já existe um fornecedor com o código {code!r}."
            )
        supplier_id = self._repository.create_supplier(
            code, name, nif.strip(), email.strip(), phone.strip(), notes.strip()
        )
        return self.get_supplier(supplier_id)

    def update_supplier(
        self,
        supplier_id: int,
        name: str,
        nif: str = "",
        email: str = "",
        phone: str = "",
        notes: str = "",
    ) -> Supplier:
        self.get_supplier(supplier_id)
        name = name.strip()
        if not name:
            raise ValueError("O nome do fornecedor não pode estar vazio.")
        self._repository.update_supplier(
            supplier_id, name, nif.strip(), email.strip(), phone.strip(), notes.strip()
        )
        return self.get_supplier(supplier_id)

    def set_active(self, supplier_id: int, active: bool) -> Supplier:
        self.get_supplier(supplier_id)
        self._repository.set_active(supplier_id, active)
        return self.get_supplier(supplier_id)

    def get_supplier(self, supplier_id: int) -> Supplier:
        record = self._repository.get_supplier(int(supplier_id))
        if record is None:
            raise SupplierNotFoundError(f"Fornecedor não encontrado: {supplier_id}.")
        return self._supplier_from_record(record)

    def list_suppliers(self, active_only: bool = False) -> list[Supplier]:
        return [
            self._supplier_from_record(record)
            for record in self._repository.list_suppliers(active_only=active_only)
        ]

    def upsert_material(
        self,
        supplier_id: int,
        material_code: str,
        unit_price: float,
        lead_time_days: int = 0,
        minimum_order_quantity: float = 0,
    ) -> SupplierMaterial:
        supplier = self.get_supplier(supplier_id)
        if not supplier.active:
            raise SupplierCatalogError(
                "O fornecedor está inativo. Ative-o antes de alterar o catálogo."
            )

        material = self._inventory_service.get_material(material_code)
        unit_price = float(unit_price)
        lead_time_days = int(lead_time_days)
        minimum_order_quantity = float(minimum_order_quantity)

        if unit_price < 0:
            raise ValueError("O preço unitário não pode ser negativo.")
        if lead_time_days < 0:
            raise ValueError("O prazo de entrega não pode ser negativo.")
        if minimum_order_quantity < 0:
            raise ValueError("A quantidade mínima de compra não pode ser negativa.")

        self._repository.upsert_material(
            supplier_id,
            material.code,
            unit_price,
            lead_time_days,
            minimum_order_quantity,
        )
        return self.get_supplier_material(supplier_id, material.code)

    def remove_material(self, supplier_id: int, material_code: str) -> None:
        self.get_supplier(supplier_id)
        material = self._inventory_service.get_material(material_code)
        if not self._repository.remove_material(supplier_id, material.code):
            raise SupplierCatalogError(
                f"O material {material.code!r} não está no catálogo deste fornecedor."
            )

    def get_supplier_material(self, supplier_id: int, material_code: str) -> SupplierMaterial:
        self.get_supplier(supplier_id)
        material = self._inventory_service.get_material(material_code)
        record = self._repository.get_supplier_material(supplier_id, material.code)
        if record is None:
            raise SupplierCatalogError(
                f"O fornecedor não possui preço cadastrado para {material.code}."
            )
        return SupplierMaterial(
            id=record.id,
            supplier_id=record.supplier_id,
            material_code=record.material_code,
            material_name=material.name,
            unit=material.unit,
            unit_price=record.unit_price,
            lead_time_days=record.lead_time_days,
            minimum_order_quantity=record.minimum_order_quantity,
            updated_at=record.updated_at,
        )

    def list_supplier_materials(self, supplier_id: int) -> list[SupplierMaterial]:
        self.get_supplier(supplier_id)
        result = []
        for record in self._repository.list_supplier_materials(supplier_id):
            try:
                material = self._inventory_service.get_material(record.material_code)
            except MaterialNotFoundError:
                continue
            result.append(
                SupplierMaterial(
                    id=record.id,
                    supplier_id=record.supplier_id,
                    material_code=record.material_code,
                    material_name=material.name,
                    unit=material.unit,
                    unit_price=record.unit_price,
                    lead_time_days=record.lead_time_days,
                    minimum_order_quantity=record.minimum_order_quantity,
                    updated_at=record.updated_at,
                )
            )
        return result

    def compare_material(self, material_code: str, quantity: float = 1) -> list[MaterialQuote]:
        material = self._inventory_service.get_material(material_code)
        requested = float(quantity)
        if requested <= 0:
            raise ValueError("A quantidade para cotação deve ser maior que zero.")

        quotes = []
        for supplier, catalog in self._repository.list_material_suppliers(material.code):
            order_quantity = max(requested, catalog.minimum_order_quantity)
            quotes.append(
                MaterialQuote(
                    supplier_id=supplier.id,
                    supplier_code=supplier.code,
                    supplier_name=supplier.name,
                    material_code=material.code,
                    material_name=material.name,
                    unit=material.unit,
                    requested_quantity=requested,
                    order_quantity=order_quantity,
                    unit_price=catalog.unit_price,
                    total_price=order_quantity * catalog.unit_price,
                    lead_time_days=catalog.lead_time_days,
                    minimum_order_quantity=catalog.minimum_order_quantity,
                )
            )
        quotes.sort(key=lambda item: (item.total_price, item.lead_time_days, item.supplier_name.lower()))
        return quotes

    def quote_purchase(self, demand_ids: list[int] | None = None) -> PurchaseQuoteAnalysis:
        purchase_list = self._procurement_service.consolidated(demand_ids)
        total_materials = len(purchase_list.items)

        active_suppliers = self._repository.list_suppliers(active_only=True)
        options: list[PurchaseSupplierOption] = []

        for supplier in active_suppliers:
            quoted_items: list[MaterialQuote] = []
            for item in purchase_list.items:
                catalog = self._repository.get_supplier_material(supplier.id, item.material_code)
                if catalog is None:
                    continue
                order_quantity = max(item.quantity_to_buy, catalog.minimum_order_quantity)
                quoted_items.append(
                    MaterialQuote(
                        supplier_id=supplier.id,
                        supplier_code=supplier.code,
                        supplier_name=supplier.name,
                        material_code=item.material_code,
                        material_name=item.material_name,
                        unit=item.unit,
                        requested_quantity=item.quantity_to_buy,
                        order_quantity=order_quantity,
                        unit_price=catalog.unit_price,
                        total_price=order_quantity * catalog.unit_price,
                        lead_time_days=catalog.lead_time_days,
                        minimum_order_quantity=catalog.minimum_order_quantity,
                    )
                )

            covered = len(quoted_items)
            if covered == 0:
                continue
            options.append(
                PurchaseSupplierOption(
                    supplier_id=supplier.id,
                    supplier_code=supplier.code,
                    supplier_name=supplier.name,
                    covered_materials=covered,
                    total_materials=total_materials,
                    full_coverage=(covered == total_materials),
                    total_estimated=sum(item.total_price for item in quoted_items),
                    max_lead_time_days=max((item.lead_time_days for item in quoted_items), default=0),
                    items=quoted_items,
                )
            )

        options.sort(
            key=lambda option: (
                not option.full_coverage,
                option.total_estimated if option.full_coverage else float("inf"),
                -option.covered_materials,
                option.max_lead_time_days,
                option.supplier_name.lower(),
            )
        )

        full_options = [option for option in options if option.full_coverage]
        best = full_options[0] if full_options else None

        best_mix: list[MaterialQuote] = []
        for item in purchase_list.items:
            quotes = self.compare_material(item.material_code, item.quantity_to_buy)
            if quotes:
                best_mix.append(quotes[0])
        best_mix_total = (
            sum(item.total_price for item in best_mix)
            if len(best_mix) == total_materials and total_materials > 0
            else None
        )

        if total_materials == 0:
            analysis = "Não há materiais para cotar com os dados atuais."
        elif best:
            analysis = (
                f"Melhor fornecedor único: {best.supplier_name}, "
                f"total estimado €{best.total_estimated:.2f}, "
                f"prazo máximo {best.max_lead_time_days} dia(s)."
            )
            if best_mix_total is not None and best_mix_total < best.total_estimated:
                analysis += (
                    f" Comprando cada item no fornecedor mais barato, o total estimado "
                    f"cai para €{best_mix_total:.2f}."
                )
        else:
            analysis = (
                "Nenhum fornecedor ativo cobre todos os materiais da lista. "
                "A Kynka calculou a melhor opção por material quando houver preço cadastrado."
            )

        return PurchaseQuoteAnalysis(
            demand_ids=purchase_list.demand_ids,
            demand_codes=purchase_list.demand_codes,
            total_materials=total_materials,
            options=options,
            best_supplier_id=best.supplier_id if best else None,
            best_supplier_name=best.supplier_name if best else None,
            best_total_estimated=best.total_estimated if best else None,
            best_mix_total=best_mix_total,
            best_mix=best_mix,
            analysis=analysis,
        )

    def pricing_for_supplier(self, supplier_id: int, purchase_items) -> tuple[Supplier, dict[str, dict[str, float]]]:
        supplier = self.get_supplier(supplier_id)
        if not supplier.active:
            raise SupplierCatalogError("O fornecedor selecionado está inativo.")

        pricing: dict[str, dict[str, float]] = {}
        missing = []
        for item in purchase_items:
            catalog = self._repository.get_supplier_material(supplier.id, item.material_code)
            if catalog is None:
                missing.append(item.material_code)
                continue
            order_quantity = max(item.quantity_to_buy, catalog.minimum_order_quantity)
            pricing[item.material_code] = {
                "unit_price": catalog.unit_price,
                "order_quantity": order_quantity,
                "total_price": order_quantity * catalog.unit_price,
            }

        if missing:
            raise SupplierCatalogError(
                "O fornecedor não possui preço cadastrado para: " + ", ".join(missing) + "."
            )
        return supplier, pricing

    def price_history(self, supplier_id: int, material_code: str, limit: int = 50):
        self.get_supplier(supplier_id)
        material = self._inventory_service.get_material(material_code)
        return self._repository.price_history(supplier_id, material.code, limit)

    def _find_material_in_text(self, text: str):
        normalized_text = self._normalize_text(text)
        materials = self._inventory_service.list_materials()
        for material in materials:
            code = self._normalize_text(material.code)
            if code and code in normalized_text:
                return material
        for material in materials:
            name = self._normalize_text(material.name)
            if name and name in normalized_text:
                return material
        return None

    def _find_demand_in_text(self, text: str):
        normalized_text = self._normalize_text(text)
        demands = self._demand_repository.list_demands()
        for demand in demands:
            if self._normalize_text(demand.code) in normalized_text:
                return demand
        for demand in demands:
            name = self._normalize_text(demand.name)
            if name and name in normalized_text:
                return demand
        return None

    def try_answer(self, text: str) -> str | None:
        normalized = self._normalize_text(text)
        supplier_terms = (
            "fornecedor",
            "fornecedores",
            "quem vende",
            "onde comprar",
            "onde devo comprar",
            "onde compro",
            "onde posso comprar",
            "onde comprar os materiais",
            "mais barato",
            "melhor preco",
            "melhor preço",
            "quanto vou gastar",
            "quanto custa comprar",
            "cotacao",
            "cotação",
        )
        if not any(self._normalize_text(term) in normalized for term in supplier_terms):
            return None

        demand = self._find_demand_in_text(text)
        if demand is not None and any(term in normalized for term in ("obra", "projeto", "gastar", "comprar", "fornecedor")):
            analysis = self.quote_purchase([demand.id])
            return analysis.analysis

        material = self._find_material_in_text(text)
        if material is None:
            return None

        quotes = self.compare_material(material.code, 1)
        if not quotes:
            return f"Não há fornecedor ativo com preço cadastrado para {material.code} — {material.name}."

        if "quem vende" in normalized or "fornecedores" in normalized:
            lines = [f"Fornecedores de {material.code} — {material.name}:"]
            for quote in quotes[:8]:
                lines.append(
                    f"{quote.supplier_name}: €{quote.unit_price:.2f}/{material.unit}, "
                    f"prazo {quote.lead_time_days} dia(s)."
                )
            return "\n".join(lines)

        best = quotes[0]
        return (
            f"Melhor preço cadastrado para {material.code} — {material.name}: "
            f"{best.supplier_name}, €{best.unit_price:.2f}/{material.unit}, "
            f"prazo {best.lead_time_days} dia(s)."
        )
