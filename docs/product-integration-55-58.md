
# Kynka Production 1.0 — Product Integration 55–58

## Architectural decision
The Kynka business domain currently remains operational on the legacy SQLite
repositories. Etapas 55–58 do not hide that fact and do not perform a risky
implicit cutover.

A versioned PostgreSQL migration (`0055_0001`) now creates a tenant-scoped
business schema for Inventory, Demand, Suppliers, Procurement, Material
Requests, Documents and Quote Imports. Tenant ownership is represented by
`organization_id`, and business uniqueness is organization-scoped where
appropriate.

## Product contract
`GET /api/v1/product/readiness` is authenticated by the existing security
middleware and exposes a machine-readable capability/readiness manifest for
web/mobile/agent clients.

## Release gate
The manifest deliberately reports `postgresql_repository_cutover_ready=false`.
Production 1.0 release remains blocked until:
1. PostgreSQL repository implementations have equivalence tests.
2. business repositories enforce tenant scope during runtime.
3. operational data migration/cutover is rehearsed and validated.

This distinction prevents "schema exists" from being confused with "the product
is running its business workload on PostgreSQL".
