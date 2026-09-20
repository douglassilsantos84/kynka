from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True, slots=True)
class ProductModuleStatus:
    module: str
    operational_backend: str
    postgresql_schema: bool
    tenant_schema: bool
    postgresql_repository: bool

MODULES = (
    "inventory", "demand", "suppliers", "procurement",
    "material_requests", "documents", "quote_imports",
)

def product_modules() -> list[ProductModuleStatus]:
    # Etapas 55-58 deliberately separate schema readiness from repository cutover.
    # Legacy business repositories are still SQLite until their repository ports
    # have PostgreSQL implementations with equivalence tests.
    return [
        ProductModuleStatus(
            module=name,
            operational_backend="sqlite",
            postgresql_schema=True,
            tenant_schema=True,
            postgresql_repository=False,
        )
        for name in MODULES
    ]

def product_readiness() -> dict:
    modules = product_modules()
    return {
        "status": "integration_foundation",
        "business_backend": "sqlite",
        "postgresql_schema_ready": all(x.postgresql_schema for x in modules),
        "tenant_schema_ready": all(x.tenant_schema for x in modules),
        "postgresql_repository_cutover_ready": all(
            x.postgresql_repository for x in modules
        ),
        "release_blockers": [
            "PostgreSQL repository implementations and equivalence tests",
            "tenant-scoped business repository cutover",
            "production data migration/cutover procedure",
        ],
        "modules": [asdict(x) for x in modules],
    }
