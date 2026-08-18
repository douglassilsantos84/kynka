"""
Capabilities de inventário da plataforma Kynka.
"""

from __future__ import annotations

from typing import Any

from kynka.application.inventory import (
    InventoryService,
)
from kynka.domain.capabilities import (
    Capability,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityResult,
)


def _format_material(
    material: Any,
) -> str:

    return (
        f"{material.code} — {material.name}: "
        f"{material.quantity:g} {material.unit} "
        f"(mínimo {material.minimum_quantity:g})"
    )


class InventorySearchCapability(
    Capability
):
    """
    Pesquisa materiais pelo código ou nome.
    """

    def __init__(
        self,
        service: InventoryService,
    ) -> None:

        super().__init__(
            CapabilityMetadata(
                name="inventory.search",
                description=(
                    "Consulta quantidade, saldo, stock, "
                    "estoque ou informações de um material "
                    "pelo código ou nome."
                ),
                version="1.0.0",
                parameters=(
                    CapabilityParameter(
                        name="query",
                        description=(
                            "Código, nome ou descrição "
                            "do material procurado."
                        ),
                        type="string",
                        required=True,
                    ),
                ),
            )
        )

        self._service = service

    def execute(
        self,
        **kwargs: Any,
    ) -> CapabilityResult:

        query = str(
            kwargs.get(
                "query",
                "",
            )
        ).strip()

        if not query:
            return CapabilityResult(
                success=False,
                error=(
                    "É necessário informar "
                    "o material a consultar."
                ),
            )

        materials = (
            self._service.search_materials(
                query
            )
        )

        if not materials:
            return CapabilityResult(
                success=False,
                error=(
                    "Nenhum material encontrado "
                    f"para {query!r}."
                ),
            )

        if len(materials) == 1:
            return CapabilityResult(
                success=True,
                data=_format_material(
                    materials[0]
                ),
            )

        return CapabilityResult(
            success=True,
            data="\n".join(
                _format_material(material)
                for material in materials
            ),
        )


class InventoryListCapability(
    Capability
):

    def __init__(
        self,
        service: InventoryService,
    ) -> None:

        super().__init__(
            CapabilityMetadata(
                name="inventory.list",
                description=(
                    "Lista todos os materiais "
                    "existentes no inventário."
                ),
                version="1.0.0",
            )
        )

        self._service = service

    def execute(
        self,
        **kwargs: Any,
    ) -> CapabilityResult:

        materials = (
            self._service.list_materials()
        )

        if not materials:
            return CapabilityResult(
                success=True,
                data="O inventário está vazio.",
            )

        return CapabilityResult(
            success=True,
            data="\n".join(
                _format_material(material)
                for material in materials
            ),
        )


class InventoryLowStockCapability(
    Capability
):

    def __init__(
        self,
        service: InventoryService,
    ) -> None:

        super().__init__(
            CapabilityMetadata(
                name="inventory.low_stock",
                description=(
                    "Lista materiais cuja quantidade "
                    "está abaixo do estoque mínimo."
                ),
                version="1.0.0",
            )
        )

        self._service = service

    def execute(
        self,
        **kwargs: Any,
    ) -> CapabilityResult:

        materials = (
            self._service.list_below_minimum()
        )

        if not materials:
            return CapabilityResult(
                success=True,
                data=(
                    "Nenhum material está abaixo "
                    "do estoque mínimo."
                ),
            )

        return CapabilityResult(
            success=True,
            data="\n".join(
                _format_material(material)
                for material in materials
            ),
        )


class InventorySummaryCapability(
    Capability
):

    def __init__(
        self,
        service: InventoryService,
    ) -> None:

        super().__init__(
            CapabilityMetadata(
                name="inventory.summary",
                description=(
                    "Mostra indicadores e situação "
                    "geral do inventário."
                ),
                version="1.0.0",
            )
        )

        self._service = service

    def execute(
        self,
        **kwargs: Any,
    ) -> CapabilityResult:

        summary = (
            self._service.summary()
        )

        return CapabilityResult(
            success=True,
            data=(
                f"Materiais cadastrados: "
                f"{summary.total_materials}\n"
                f"Abaixo do mínimo: "
                f"{summary.below_minimum}\n"
                f"Sem estoque: "
                f"{summary.zero_stock}"
            ),
        )