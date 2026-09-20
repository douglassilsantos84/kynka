from __future__ import annotations
from pathlib import Path
from kynka.product_integration import product_modules, product_readiness

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {x.module for x in product_modules()}
PATHS = {
    "inventory": ROOT/"src/kynka/infrastructure/inventory/sqlite_inventory_repository.py",
    "demand": ROOT/"src/kynka/infrastructure/demand/sqlite_demand_repository.py",
    "suppliers": ROOT/"src/kynka/infrastructure/suppliers/sqlite_supplier_repository.py",
    "procurement": ROOT/"src/kynka/infrastructure/procurement/sqlite_purchase_order_repository.py",
    "material_requests": ROOT/"src/kynka/infrastructure/material_requests/sqlite_material_request_repository.py",
    "documents": ROOT/"src/kynka/infrastructure/documents/sqlite_document_repository.py",
    "quote_imports": ROOT/"src/kynka/infrastructure/quote_imports/sqlite_quote_import_repository.py",
}
missing = EXPECTED - set(PATHS)
if missing:
    raise SystemExit("Manifesto incompleto: " + ", ".join(sorted(missing)))
for module, path in PATHS.items():
    if not path.exists():
        raise SystemExit(f"Repositorio esperado ausente: {module}: {path}")
state = product_readiness()
print("===== KYNKA PRODUCT INTEGRATION AUDIT =====")
print("business_backend:", state["business_backend"])
print("postgresql_schema_ready:", state["postgresql_schema_ready"])
print("tenant_schema_ready:", state["tenant_schema_ready"])
print("postgresql_repository_cutover_ready:", state["postgresql_repository_cutover_ready"])
for item in state["modules"]:
    print(
        item["module"],
        "backend="+item["operational_backend"],
        "pg_schema="+str(item["postgresql_schema"]),
        "tenant_schema="+str(item["tenant_schema"]),
        "pg_repo="+str(item["postgresql_repository"]),
    )
print("Release blockers:", len(state["release_blockers"]))
print("AUDIT: PASSED")
