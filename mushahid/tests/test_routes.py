import pytest
from mushahid.routes.health import health_check


# ── Health endpoint — partially implemented, test directly ───────────────────

async def test_health_check_returns_ok():
    response = await health_check()
    assert "status" in response


# ── Auth enforcement — HTTP pattern (needs routers registered in main.py) ─────
# Uncomment include_router calls in mushahid/main.py, then remove the pytest.skip.

PROTECTED_ROUTES = [
    ("POST", "/plan-trip"),
    ("POST", "/update-trip"),
    ("POST", "/cotraveller"),
    ("POST", "/chat/start"),
    ("POST", "/chat/approve"),
    ("POST", "/chat/deny"),
]


@pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
async def test_protected_routes_return_401_without_token(client):
    pytest.skip("Uncomment routers in mushahid/main.py first")
    response = await client.request(method, path)
    assert response.status_code == 401


async def test_protected_route_succeeds_with_auth_override(client, override_auth):
    pytest.skip("Uncomment routers in mushahid/main.py first")
    response = await client.get("/users/profile")
    assert response.status_code != 401
