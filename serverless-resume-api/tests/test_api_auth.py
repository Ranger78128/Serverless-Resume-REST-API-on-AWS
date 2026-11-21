"""
Integration tests for API Gateway Authentication & Throttling simulation.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.web_app import app, DEMO_API_KEY

client = TestClient(app)


def test_resume_endpoint_without_api_key_forbidden():
    res = client.post("/api/simulate-apigateway", json={
        "path": "/resume",
        "http_method": "GET",
        "api_key": None
    })
    assert res.status_code == 403
    data = res.json()
    assert "Forbidden" in data["message"]
    assert "x-api-key required" in data["error"]


def test_resume_endpoint_with_invalid_api_key_forbidden():
    res = client.post("/api/simulate-apigateway", json={
        "path": "/resume/personal",
        "http_method": "GET",
        "api_key": "fraudulent-key-xyz"
    })
    assert res.status_code == 403
    data = res.json()
    assert "Invalid API Key" in data["error"]


def test_resume_endpoint_with_valid_api_key_success():
    res = client.post("/api/simulate-apigateway", json={
        "path": "/resume/personal",
        "http_method": "GET",
        "api_key": DEMO_API_KEY
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["data"]["name"] == "Alex Vance"

    # Check Usage Plan headers
    headers = res.headers
    assert "X-RateLimit-Limit" in headers
    assert "X-RateLimit-Remaining" in headers
    assert "X-Burst-Limit" in headers


def test_health_endpoint_without_api_key_success():
    # Public health endpoint does not require an API key
    res = client.post("/api/simulate-apigateway", json={
        "path": "/health",
        "http_method": "GET",
        "api_key": None
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
