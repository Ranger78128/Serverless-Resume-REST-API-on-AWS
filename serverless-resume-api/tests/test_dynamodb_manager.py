"""
Unit tests for DynamoDB Manager using moto.
"""

import os
import sys
import boto3
import moto
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.dynamodb_manager import DynamoDBManager


@pytest.fixture
def dynamodb_env():
    with moto.mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        mgr = DynamoDBManager(dynamodb_resource=dynamodb, table_name="TestResumeTable")
        mgr.create_table_if_not_exists()
        yield mgr


def test_create_and_seed_dynamodb(dynamodb_env):
    mgr = dynamodb_env
    json_path = os.path.join(PROJECT_ROOT, "data", "resume_data.json")

    # Seed table
    count = mgr.seed_from_json(json_path)
    assert count > 5

    # Query personal section
    personal = mgr.get_section("personal")
    assert personal is not None
    assert personal["name"] == "Alex Vance"

    # Query experience section
    exp = mgr.get_section("experience")
    assert exp is not None
    assert len(exp) >= 3

    # Query skills section
    skills = mgr.get_section("skills")
    assert skills is not None
    assert "cloud_and_serverless" in skills

    # Full aggregate query
    full = mgr.get_full_resume()
    assert "personal" in full
    assert "experience" in full
    assert "education" in full
    assert "skills" in full
