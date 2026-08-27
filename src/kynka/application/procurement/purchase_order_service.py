"""Caso de uso de pedidos de compra e recebimento."""

from __future__ import annotations

from dataclasses import dataclass

from kynka.application.inventory import InventoryService
from kynka.infrastructure.procurement import SQLitePurchaseOrderRepository

from .procurement_service import ProcurementService


class PurchaseOrderNotFoundError(Exception):
    pass


class PurchaseOrderStateError(Exception):
    pass


class PurchaseOrderDuplicateError(Exception):
    pass


@dataclass(slots=True)
class PurchaseOrderItem:
    id: int
    material_code: str
    material_name: str
    unit: str
    quantity_ordered: float
    quantity_received: float
    quantity_pending: float


@dataclass(slots=True)
class PurchaseOrder:
    id: int
    status: str
    demand_ids: list[int]
    demand_codes: list[str]
    notes: str
    created_at: str
    ordered_at: str | None
    completed_at: str | None
    items: list[PurchaseOrderItem]


class PurchaseOrderService:
    ACTIVE_STATUSES = {
        "draft",
        "ordered",
        "partially_received",
    }

    def __init__(
        self,
        repository: SQLitePurchaseOrderRepository,
        procurement_service: ProcurementService,
        inventory_service: InventoryService,
    ) -> None:
        self._repository = repository
        self._procurement_service = procurement_service
        self._inventory_service = inventory_service

    def create(
        self,
        demand_ids: list[int] | None = None,
        notes: str = "",
    ) -> PurchaseOrder:
        purchase_list = self._procurement_service.consolidated(
            demand_ids
        )

        if not purchase_list.items:
            raise ValueError(
                "Não há materiais para gerar um pedido de compra."
            )

        self._validate_no_duplicate_pending_items(
            purchase_list.demand_ids,
            purchase_list.items,
        )

        order_id = self._repository.create_order(
            purchase_list.demand_ids,
            purchase_list.demand_codes,
            notes,
            purchase_list.items,
        )

        return self.get(order_id)

    def _validate_no_duplicate_pending_items(
        self,
        demand_ids: list[int],
        purchase_items,
    ) -> None:
        requested_demand_ids = {
            int(demand_id)
            for demand_id in demand_ids
        }

        materials_to_create = {
            item.material_code
            for item in purchase_items
            if item.quantity_to_buy > 0
        }

        conflicts = []

        for record in self._repository.list_orders():
            if record.status not in self.ACTIVE_STATUSES:
                continue

            existing_demand_ids = {
                int(demand_id)
                for demand_id in record.demand_ids
            }

            if not (
                requested_demand_ids
                & existing_demand_ids
            ):
                continue

            for item in self._repository.get_items(record.id):
                if item.quantity_pending <= 0:
                    continue

                if item.material_code not in materials_to_create:
                    continue

                conflicts.append(
                    (
                        record.id,
                        item.material_code,
                        item.material_name,
                        item.quantity_pending,
                        item.unit,
                    )
                )

        if not conflicts:
            return

        lines = [
            "Já existe pedido de compra ativo para "
            "material(is) desta necessidade:"
        ]

        for (
            order_id,
            material_code,
            material_name,
            quantity_pending,
            unit,
        ) in conflicts:
            lines.append(
                f"Pedido #{order_id} — "
                f"{material_code} — "
                f"{material_name}: "
                f"{quantity_pending:g} {unit} pendente(s)."
            )

        lines.append(
            "Receba ou cancele o pedido existente antes "
            "de gerar outro pedido para o mesmo material."
        )

        raise PurchaseOrderDuplicateError(
            "\n".join(lines)
        )

    def list_orders(self) -> list[PurchaseOrder]:
        return [
            self.get(record.id)
            for record in self._repository.list_orders()
        ]

    def get(self, order_id: int) -> PurchaseOrder:
        record = self._repository.get_order(order_id)

        if record is None:
            raise PurchaseOrderNotFoundError(
                f"Pedido de compra não encontrado: {order_id}."
            )

        items = [
            PurchaseOrderItem(
                id=item.id,
                material_code=item.material_code,
                material_name=item.material_name,
                unit=item.unit,
                quantity_ordered=item.quantity_ordered,
                quantity_received=item.quantity_received,
                quantity_pending=item.quantity_pending,
            )
            for item in self._repository.get_items(order_id)
        ]

        return PurchaseOrder(
            id=record.id,
            status=record.status,
            demand_ids=record.demand_ids,
            demand_codes=record.demand_codes,
            notes=record.notes,
            created_at=record.created_at,
            ordered_at=record.ordered_at,
            completed_at=record.completed_at,
            items=items,
        )

    def mark_ordered(
        self,
        order_id: int,
    ) -> PurchaseOrder:
        order = self.get(order_id)

        if order.status != "draft":
            raise PurchaseOrderStateError(
                "Somente pedidos em rascunho podem ser "
                "marcados como enviados ao fornecedor."
            )

        self._repository.set_status(
            order_id,
            "ordered",
        )

        return self.get(order_id)

    def cancel(
        self,
        order_id: int,
    ) -> PurchaseOrder:
        order = self.get(order_id)

        if order.status == "received":
            raise PurchaseOrderStateError(
                "Um pedido totalmente recebido não pode "
                "ser cancelado."
            )

        self._repository.set_status(
            order_id,
            "cancelled",
        )

        return self.get(order_id)

    def receive(
        self,
        order_id: int,
        item_id: int,
        quantity: float,
    ) -> PurchaseOrder:
        order = self.get(order_id)

        if order.status not in {
            "ordered",
            "partially_received",
        }:
            raise PurchaseOrderStateError(
                "O pedido precisa estar enviado ao "
                "fornecedor antes do recebimento."
            )

        item_record = self._repository.get_item(
            item_id
        )

        if (
            item_record is None
            or item_record.order_id != order_id
        ):
            raise PurchaseOrderNotFoundError(
                "Item do pedido não encontrado."
            )

        quantity = float(quantity)

        if quantity <= 0:
            raise ValueError(
                "A quantidade recebida deve ser "
                "maior que zero."
            )

        if quantity > item_record.quantity_pending:
            raise ValueError(
                "Quantidade recebida superior ao "
                "pendente. "
                f"Pendente: "
                f"{item_record.quantity_pending:g} "
                f"{item_record.unit}."
            )

        material = self._inventory_service.get_material(
            item_record.material_code
        )

        previous_quantity = material.quantity

        try:
            self._inventory_service.add_entry(
                item_record.material_code,
                quantity,
                (
                    "Recebimento pedido de compra "
                    f"#{order_id}"
                ),
            )

            self._repository.add_received(
                item_id,
                quantity,
            )

        except Exception:
            # Compensação enquanto não houver uma
            # Unit of Work compartilhada.
            try:
                self._inventory_service.adjust_stock(
                    item_record.material_code,
                    previous_quantity,
                    (
                        "Compensação de falha no "
                        "recebimento do pedido "
                        f"#{order_id}"
                    ),
                )
            except Exception:
                pass

            raise

        refreshed = self.get(order_id)

        pending = sum(
            item.quantity_pending
            for item in refreshed.items
        )

        new_status = (
            "received"
            if pending <= 0
            else "partially_received"
        )

        self._repository.set_status(
            order_id,
            new_status,
        )

        return self.get(order_id)

    def try_answer(
        self,
        text: str,
    ) -> str | None:
        normalized = text.strip().lower()

        terms = (
            "pedidos de compra",
            "pedido de compra",
            "compras pendentes",
            "compras ainda não chegaram",
            "compras ainda nao chegaram",
            "pedidos pendentes",
            "recebimentos pendentes",
        )

        if not any(
            term in normalized
            for term in terms
        ):
            return None

        orders = [
            order
            for order in self.list_orders()
            if order.status
            not in {"received", "cancelled"}
        ]

        if not orders:
            return (
                "Não há pedidos de compra pendentes."
            )

        lines = [
            f"Há {len(orders)} pedido(s) de "
            "compra pendente(s)."
        ]

        for order in orders[:8]:
            pending_items = sum(
                1
                for item in order.items
                if item.quantity_pending > 0
            )

            scope = (
                ", ".join(order.demand_codes)
                or "consolidado"
            )

            lines.append(
                f"Pedido #{order.id} — "
                f"{scope} — "
                f"status {order.status} — "
                f"{pending_items} item(ns) "
                "pendente(s)."
            )

        return "\n".join(lines)
