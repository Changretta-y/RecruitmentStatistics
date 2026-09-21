import json

import pytest
from django.test import Client


@pytest.fixture
def client():
    """Provide Django's public test client without importing production code."""
    return Client()


def test_health_get_returns_strict_ok_json(client):
    response = client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert response.content == b'{"status":"ok"}'
    assert json.loads(response.content) == {"status": "ok"}


def test_health_post_is_not_allowed(client):
    response = client.post("/api/v1/health/")

    assert response.status_code == 405
