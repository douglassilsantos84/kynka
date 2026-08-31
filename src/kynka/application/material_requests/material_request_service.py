from __future__ import annotations


class MaterialRequestService:
    PRIORITIES = {"low", "normal", "high", "urgent"}

    TRANSITIONS = {
        "requested": {"approved", "cancelled"},
        "approved": {"separating", "cancelled"},
        "separating": {"ready", "shortage", "cancelled"},
        "shortage": {"separating", "ready", "cancelled"},
        "ready": {"delivered", "cancelled"},
        "delivered": set(),
        "cancelled": set(),
    }

    def __init__(
        self,
        repository,
        demand_service,
        demand_repository,
        inventory_service,
    ):
        self.repository = repository
        self.demand_service = demand_service
        self.demand_repository = demand_repository
        self.inventory_service = inventory_service

    def _get_demand(self, demand_id: int):
        return self.demand_service.get_demand(int(demand_id))

    def _get_material(self, material_code: str):
        return self.inventory_service.get_material(material_code)

    def _free_quantity(self, material) -> float:
        reserved_total = float(
            self.demand_repository.total_reserved(material.code)
        )
        return max(
            float(material.quantity)
            - float(material.minimum_quantity)
            - reserved_total,
            0.0,
        )

    def create(
        self,
        demand_id,
        requester,
        items,
        priority="normal",
        notes="",
    ):
        demand = self._get_demand(demand_id)

        requester = str(requester).strip()
        priority = str(priority).strip().lower()

        if not requester:
            raise ValueError("Informe o funcionario solicitante.")

        if priority not in self.PRIORITIES:
            raise ValueError("Prioridade invalida.")

        if not items:
            raise ValueError("Adicione pelo menos um material.")

        prepared_items = []
        seen = set()

        for item in items:
            code = str(item.get("material_code", "")).strip()
            quantity = float(item.get("quantity", 0))

            if not code or quantity <= 0:
                raise ValueError(
                    "Material e quantidade devem ser validos."
                )

            material = self._get_material(code)
            normalized_code = material.code

            if normalized_code in seen:
                raise ValueError(
                    f"Material duplicado: {normalized_code}."
                )

            seen.add(normalized_code)

            free_quantity = self._free_quantity(material)
            available = min(quantity, free_quantity)

            prepared_items.append(
                {
                    "material_code": material.code,
                    "material_name": material.name,
                    "unit": material.unit,
                    "quantity_requested": quantity,
                    "quantity_available": available,
                    "shortage_quantity": max(
                        quantity - available,
                        0.0,
                    ),
                }
            )

        request_id = self.repository.create(
            demand.id,
            requester,
            priority,
            str(notes).strip(),
            prepared_items,
        )

        return self.get(request_id)

    def get(self, request_id):
        request = self.repository.get(int(request_id))

        if not request:
            raise ValueError("Solicitacao nao encontrada.")

        demand = self._get_demand(request["demand_id"])

        request["demand_code"] = demand.code
        request["demand_name"] = demand.name
        request["items"] = self.repository.items(request["id"])
        request["events"] = self.repository.events(request["id"])
        request["has_shortage"] = any(
            float(item["shortage_quantity"]) > 0
            for item in request["items"]
        )

        return request

    def list(self, status=None, demand_id=None):
        if status:
            status = str(status).strip().lower()

        return [
            self.get(row["id"])
            for row in self.repository.list(
                status=status,
                demand_id=demand_id,
            )
        ]

    def transition(
        self,
        request_id,
        status,
        actor="",
        notes="",
    ):
        request = self.get(request_id)
        status = str(status).strip().lower()

        allowed = self.TRANSITIONS.get(
            request["status"],
            set(),
        )

        if status not in allowed:
            raise ValueError(
                "Transicao invalida: "
                f"{request['status']} -> {status}."
            )

        self.repository.transition(
            request_id,
            status,
            str(actor).strip(),
            str(notes).strip(),
        )

        return self.get(request_id)

    def separate(
        self,
        request_id,
        actor="",
        notes="",
    ):
        request = self.get(request_id)

        if request["status"] not in {
            "approved",
            "shortage",
            "separating",
        }:
            raise ValueError(
                "A solicitacao precisa estar aprovada "
                "para separacao."
            )

        separated_values = {}
        shortage = False

        for item in request["items"]:
            material = self._get_material(
                item["material_code"]
            )

            free_quantity = self._free_quantity(material)

            quantity_requested = float(
                item["quantity_requested"]
            )
            quantity_separated = min(
                quantity_requested,
                free_quantity,
            )

            separated_values[material.code] = (
                quantity_separated
            )

            if quantity_separated < quantity_requested:
                shortage = True

        self.repository.separation(
            request_id,
            separated_values,
        )

        current_status = request["status"]

        if current_status == "approved":
            self.repository.transition(
                request_id,
                "separating",
                str(actor).strip(),
                str(notes).strip(),
            )

        target_status = (
            "shortage"
            if shortage
            else "ready"
        )

        self.repository.transition(
            request_id,
            target_status,
            str(actor).strip(),
            str(notes).strip(),
        )

        return self.get(request_id)

    def deliver(
        self,
        request_id,
        actor="",
        notes="",
    ):
        request = self.get(request_id)

        if request["status"] != "ready":
            raise ValueError(
                "Somente uma solicitacao pronta "
                "pode ser entregue."
            )

        delivery_items = []

        # Primeiro valida TODOS os itens. Nenhuma baixa acontece
        # enquanto existir um item inconsistente.
        for item in request["items"]:
            quantity = float(
                item["quantity_separated"]
            )

            if quantity <= 0:
                raise ValueError(
                    "A solicitacao possui item sem quantidade "
                    f"separada: {item['material_code']}."
                )

            material = self._get_material(
                item["material_code"]
            )

            if quantity > float(material.quantity):
                raise ValueError(
                    "Estoque insuficiente para "
                    f"{material.code}. "
                    f"Saldo atual: {material.quantity:g} "
                    f"{material.unit}."
                )

            delivery_items.append(
                (material.code, quantity)
            )

        # A movimentacao passa pela camada oficial do inventario,
        # preservando MovementType.EXIT e o historico existente.
        for material_code, quantity in delivery_items:
            self.inventory_service.add_exit(
                material_code,
                quantity,
                (
                    f"Entrega {request['code']} - "
                    f"{request['demand_code']}"
                ),
            )

        self.repository.transition(
            request_id,
            "delivered",
            str(actor).strip(),
            str(notes).strip(),
        )

        return self.get(request_id)

    def summary(self):
        return self.repository.summary()
