from pathlib import Path
import pytest
from kynka.security.security import LoginRateLimiter, SecurityService, SecurityStore

@pytest.fixture()
def service(tmp_path: Path):
    return SecurityService(
        SecurityStore(tmp_path / "security.db"),
        LoginRateLimiter(max_attempts=3, window_seconds=300),
    )

def bootstrap(service):
    return service.bootstrap("Org Alpha", "Admin Alpha", "admin@alpha.test", "SenhaForte2026!")

def test_bootstrap_and_authentication(service):
    result = bootstrap(service)
    identity = service.authenticate(result["access_token"])
    assert identity["role"] == "admin"
    assert identity["organization_name"] == "Org Alpha"

def test_role_change_revokes_existing_tokens(service):
    admin = bootstrap(service)
    identity = service.authenticate(admin["access_token"])
    worker = service.create_user(
        identity, "Worker", "worker@alpha.test", "OutraSenha2026!", "worker"
    )
    login = service.login("worker@alpha.test", "OutraSenha2026!", "test-client")
    service.store.set_user(worker["id"], identity["organization_id"], role="buyer")
    with pytest.raises(ValueError):
        service.authenticate(login["access_token"])

def test_login_rate_limit(service):
    for _ in range(3):
        with pytest.raises(ValueError):
            service.login("nobody@test.local", "wrong", "127.0.0.9")
    with pytest.raises(PermissionError):
        service.login("nobody@test.local", "wrong", "127.0.0.9")

def test_cross_tenant_user_mutation_is_blocked(service):
    admin = bootstrap(service)
    identity = service.authenticate(admin["access_token"])
    worker = service.create_user(
        identity, "Worker", "worker@alpha.test", "OutraSenha2026!", "worker"
    )
    connection = service.store.connect()
    try:
        beta = connection.execute(
            "INSERT INTO organizations(name,created_at) VALUES(?,?)",
            ("Org Beta", service.store.now()),
        ).lastrowid
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError):
        service.store.set_user(worker["id"], beta, active=False)
