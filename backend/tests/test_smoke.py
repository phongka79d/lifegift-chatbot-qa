"""Smoke test verifying application startup, configuration, and health check."""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Verify GET /api/health returns 200 and healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "lifegift-chatbot"


def test_settings_load():
    """Verify settings loads successfully."""
    from backend.app.core.config import get_settings

    settings = get_settings()
    assert settings.QDRANT_COLLECTION == "lifegift_knowledge"
    assert settings.LLM_MODEL is not None
