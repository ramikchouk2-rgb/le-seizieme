import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

VALID_EMAIL = "admin@le-seizieme.local"
VALID_PASSWORD = "SecurePassword123!"

# Keys that would expose a server's personal GPS position if they ever reached
# a public API response.
FORBIDDEN_GPS_KEYS = {
    "latitude",
    "lat",
    "longitude",
    "lon",
    "lng",
    "current_latitude",
    "current_longitude",
    "pickup_latitude",
    "pickup_longitude",
    "departure_latitude",
    "departure_longitude",
    "coordinates",
    "location_coordinates",
}


def find_forbidden_keys(payload, path="$"):
    """Return every ``(path, key)`` pair in a JSON payload that exposes GPS."""
    found = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(key, str) and key.lower() in FORBIDDEN_GPS_KEYS:
                found.append((f"{path}.{key}", key))
            found.extend(find_forbidden_keys(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found.extend(find_forbidden_keys(value, f"{path}[{index}]"))
    return found


def test_unauthenticated_access_returns_401():
    r = client.get("/api/events")
    assert r.status_code == 401

    r = client.get("/api/cities")
    assert r.status_code == 401

    r = client.get("/api/servers")
    assert r.status_code == 401

    r = client.get("/api/events/00000000-0000-0000-0000-000000000000/attendance")
    assert r.status_code == 401


def test_health_is_public():
    r = client.get("/api/health")
    assert r.status_code == 200


def test_login_valid_credentials():
    r = client.post("/api/auth/login", json={"email": VALID_EMAIL, "password": VALID_PASSWORD})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == VALID_EMAIL
    assert data["user"]["role"] == "ADMIN"


def test_login_invalid_password():
    r = client.post("/api/auth/login", json={"email": VALID_EMAIL, "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user():
    r = client.post("/api/auth/login", json={"email": "unknown@test.com", "password": "wrong"})
    assert r.status_code == 401


def test_authenticated_access_with_valid_token():
    r = client.post("/api/auth/login", json={"email": VALID_EMAIL, "password": VALID_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/events", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == VALID_EMAIL


def test_invalid_jwt_returns_401():
    r = client.get("/api/events", headers={"Authorization": "Bearer invalid-token"})
    assert r.status_code == 401


def test_manager_endpoint_requires_manager_or_admin():
    r = client.post("/api/events/00000000-0000-0000-0000-000000000000/urgent-offers/generate")
    assert r.status_code == 401

    r = client.post("/api/events/00000000-0000-0000-0000-000000000000/attendance/initialize")
    assert r.status_code == 401


def test_admin_can_access_manager_endpoints():
    r = client.post("/api/auth/login", json={"email": VALID_EMAIL, "password": VALID_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.post(
        "/api/events/00000000-0000-0000-0000-000000000000/urgent-offers/generate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code in (200, 400, 404)


def test_no_password_hash_in_login_response():
    r = client.post("/api/auth/login", json={"email": VALID_EMAIL, "password": VALID_PASSWORD})
    assert r.status_code == 200
    data = r.json()
    assert "password" not in data
    assert "hashed_password" not in data
    assert "hashed" not in str(data).lower()


def test_no_raw_gps_in_transport_recommendation():
    r = client.post("/api/auth/login", json={"email": VALID_EMAIL, "password": VALID_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/api/events/00000000-0000-0000-0000-000000000000/recommend-transport",
        headers=headers,
    )
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        leaked = find_forbidden_keys(r.json())
        assert leaked == [], f"Server GPS exposed by transport recommendation: {leaked}"


def test_no_raw_gps_in_server_endpoints():
    r = client.post("/api/auth/login", json={"email": VALID_EMAIL, "password": VALID_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for method, url in (
        ("get", "/api/servers"),
        ("get", "/api/servers?location_verified=true"),
        ("get", "/api/servers/stats"),
        ("get", "/api/events"),
    ):
        resp = getattr(client, method)(url, headers=headers)
        assert resp.status_code in (200, 404), f"{url} -> {resp.status_code}"
        if resp.status_code == 200:
            leaked = find_forbidden_keys(resp.json())
            assert leaked == [], f"Server GPS exposed by {url}: {leaked}"
