from kynka.product_integration import product_modules, product_readiness
from kynka.production_data.migrations.postgresql_migrations import build_baseline_migrations

def test_product_manifest_is_explicit():
    state=product_readiness()
    assert state["business_backend"]=="sqlite"
    assert state["postgresql_schema_ready"] is True
    assert state["tenant_schema_ready"] is True
    assert state["postgresql_repository_cutover_ready"] is False
    assert len(state["release_blockers"]) == 3

def test_business_modules_are_declared():
    assert {x.module for x in product_modules()} == {
        "inventory","demand","suppliers","procurement",
        "material_requests","documents","quote_imports",
    }

def test_postgresql_business_migration_is_versioned_and_tenant_scoped():
    migrations=build_baseline_migrations()
    assert [m.version for m in migrations] == ["0040_0001","0055_0001"]
    migration=migrations[-1]
    sql="\n".join(migration.statements).lower()
    assert "organization_id" in sql
    for table in (
        "business_materials","business_demands","business_suppliers",
        "business_purchase_orders","business_material_requests",
        "business_documents","business_supplier_quote_imports",
    ):
        assert table in sql
