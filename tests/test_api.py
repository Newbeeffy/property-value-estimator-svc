"""API tests for the estimator endpoints.

The downstream model service is mocked with ``respx`` so tests never touch the
network. SQLite is pointed at a temp file via ``config.DB_PATH``.
"""
from __future__ import annotations

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app import config
from app.main import app

SAMPLE_HOUSE = {
    "square_footage": 1850,
    "bedrooms": 3,
    "bathrooms": 2,
    "year_built": 1998,
    "lot_size": 7500,
    "distance_to_city_center": 5.6,
    "school_rating": 8.2,
}


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "estimates.db"))


@pytest.fixture
def client_fixture():
    with TestClient(app) as c:
        yield c


@respx.mock
def test_health(client_fixture):
    resp = client_fixture.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@respx.mock
def test_create_estimate(client_fixture):
    respx.post(f"{config.MODEL_SERVICE_URL}/predict").mock(
        return_value=httpx.Response(200, json={"predictions": [265000.0]})
    )
    resp = client_fixture.post("/estimates", json=SAMPLE_HOUSE)
    assert resp.status_code == 201
    data = resp.json()
    assert data["prediction"] == 265000.0
    assert data["inputs"] == SAMPLE_HOUSE
    assert data["id"]


@respx.mock
def test_create_estimate_validation_error(client_fixture):
    bad = {**SAMPLE_HOUSE, "bedrooms": -1}
    resp = client_fixture.post("/estimates", json=bad)
    assert resp.status_code == 422


@respx.mock
def test_batch(client_fixture):
    respx.post(f"{config.MODEL_SERVICE_URL}/predict").mock(
        return_value=httpx.Response(200, json={"predictions": [265000.0, 186000.0]})
    )
    resp = client_fixture.post("/estimates/batch", json=[SAMPLE_HOUSE, SAMPLE_HOUSE])
    assert resp.status_code == 201
    assert [e["prediction"] for e in resp.json()["estimates"]] == [265000.0, 186000.0]


@respx.mock
def test_batch_empty(client_fixture):
    resp = client_fixture.post("/estimates/batch", json=[])
    assert resp.status_code == 422


@respx.mock
def test_upstream_unavailable_returns_503(client_fixture):
    respx.post(f"{config.MODEL_SERVICE_URL}/predict").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    resp = client_fixture.post("/estimates", json=SAMPLE_HOUSE)
    assert resp.status_code == 503


@respx.mock
def test_history_roundtrip(client_fixture):
    respx.post(f"{config.MODEL_SERVICE_URL}/predict").mock(
        return_value=httpx.Response(200, json={"predictions": [265000.0]})
    )
    created = client_fixture.post("/estimates", json=SAMPLE_HOUSE).json()

    listed = client_fixture.get("/estimates")
    assert listed.status_code == 200
    assert len(listed.json()["estimates"]) == 1

    fetched = client_fixture.get(f"/estimates/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]

    deleted = client_fixture.delete(f"/estimates/{created['id']}")
    assert deleted.status_code == 204
    assert client_fixture.get(f"/estimates/{created['id']}").status_code == 404


@respx.mock
def test_get_missing_estimate_404(client_fixture):
    assert client_fixture.get("/estimates/nope").status_code == 404
