"""
Integration tests for FastAPI web endpoints.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.web_app import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_get_resume_endpoint():
    res = client.get("/api/resume")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    assert "personal" in data["data"]


def test_get_resume_section_endpoint():
    res = client.get("/api/resume/skills")
    assert res.status_code == 200
    data = res.json()
    assert data["section"] == "skills"
    assert "cloud_and_serverless" in data["data"]


def test_get_cloudformation_yaml():
    res = client.get("/api/cloudformation")
    assert res.status_code == 200
    assert "AWSTemplateFormatVersion" in res.json()["yaml_content"]


def test_seed_dynamodb_endpoint():
    res = client.post("/api/seed-dynamodb")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "personal" in data["sections_seeded"]
