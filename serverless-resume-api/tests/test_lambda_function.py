"""
Unit tests for AWS Lambda Backend Handler.
"""

import json
import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.lambda_function import lambda_handler


def test_health_check_endpoint():
    event = {
        "httpMethod": "GET",
        "path": "/health"
    }
    res = lambda_handler(event, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["status"] == "healthy"
    assert "service" in body


def test_resume_full_endpoint():
    event = {
        "httpMethod": "GET",
        "path": "/resume"
    }
    res = lambda_handler(event, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["status"] == "success"
    assert "personal" in body["data"]
    assert "experience" in body["data"]
    assert "education" in body["data"]
    assert "skills" in body["data"]


def test_resume_personal_endpoint():
    event = {
        "httpMethod": "GET",
        "path": "/resume/personal"
    }
    res = lambda_handler(event, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["section"] == "personal"
    assert body["data"]["name"] == "Alex Vance"
    assert "title" in body["data"]
    assert "email" in body["data"]


def test_resume_experience_endpoint():
    event = {
        "httpMethod": "GET",
        "path": "/resume/experience"
    }
    res = lambda_handler(event, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["section"] == "experience"
    assert len(body["data"]) >= 3
    assert body["data"][0]["company"] == "Apex Cloud Systems"


def test_resume_education_endpoint():
    event = {
        "httpMethod": "GET",
        "path": "/resume/education"
    }
    res = lambda_handler(event, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["section"] == "education"
    assert len(body["data"]) >= 2
    assert "Berkeley" in body["data"][0]["institution"]


def test_resume_skills_endpoint():
    event = {
        "httpMethod": "GET",
        "path": "/resume/skills"
    }
    res = lambda_handler(event, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["section"] == "skills"
    assert "cloud_and_serverless" in body["data"]
    assert "AWS Lambda" in body["data"]["cloud_and_serverless"]


def test_cors_preflight_options():
    event = {
        "httpMethod": "OPTIONS",
        "path": "/resume"
    }
    res = lambda_handler(event, None)
    assert res["statusCode"] == 200
    assert "Access-Control-Allow-Origin" in res["headers"]
    assert res["headers"]["Access-Control-Allow-Origin"] == "*"


def test_method_not_allowed_post():
    event = {
        "httpMethod": "POST",
        "path": "/resume"
    }
    res = lambda_handler(event, None)
    assert res["statusCode"] == 405
    body = json.loads(res["body"])
    assert "error" in body


def test_not_found_invalid_path():
    event = {
        "httpMethod": "GET",
        "path": "/resume/invalid-path-xyz"
    }
    res = lambda_handler(event, None)
    assert res["statusCode"] == 404
    body = json.loads(res["body"])
    assert "error" in body
    assert "available_endpoints" in body
