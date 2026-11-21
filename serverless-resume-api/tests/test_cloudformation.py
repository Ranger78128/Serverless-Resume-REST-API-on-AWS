"""
Unit tests for CloudFormation Template syntax and resources.
"""

import os
import sys
import pytest
import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)


def cfn_multi_constructor(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return {tag_suffix: loader.construct_scalar(node)}
    elif isinstance(node, yaml.SequenceNode):
        return {tag_suffix: loader.construct_sequence(node)}
    elif isinstance(node, yaml.MappingNode):
        return {tag_suffix: loader.construct_mapping(node)}
    return {tag_suffix: None}


yaml.add_multi_constructor("!", cfn_multi_constructor, Loader=yaml.SafeLoader)


@pytest.fixture
def cfn_data():
    path = os.path.join(PROJECT_ROOT, "cloudformation", "template.yaml")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return yaml.safe_load(content)


def test_cfn_structure(cfn_data):
    assert "AWSTemplateFormatVersion" in cfn_data
    assert "Resources" in cfn_data
    assert "Parameters" in cfn_data
    assert "Outputs" in cfn_data


def test_cfn_core_resources(cfn_data):
    resources = cfn_data["Resources"]
    expected_resources = [
        "ServerlessResumeTable",
        "ResumeLambdaExecutionRole",
        "ResumeApiFunction",
        "ResumeRestApi",
        "ResumeApiKey",
        "ResumeApiUsagePlan",
        "ResumeApiUsagePlanKey",
        "ResumeLambdaPermission"
    ]
    for r in expected_resources:
        assert r in resources, f"Missing resource: {r}"


def test_dynamodb_schema(cfn_data):
    table = cfn_data["Resources"]["ServerlessResumeTable"]
    props = table["Properties"]
    assert props["BillingMode"] == "PAY_PER_REQUEST"

    # Check KeySchema
    key_map = {k["AttributeName"]: k["KeyType"] for k in props["KeySchema"]}
    assert key_map.get("section") == "HASH"
    assert key_map.get("id") == "RANGE"


def test_api_gateway_api_key_required(cfn_data):
    resources = cfn_data["Resources"]
    assert resources["ResumeGetMethod"]["Properties"]["ApiKeyRequired"] is True
    assert resources["PersonalGetMethod"]["Properties"]["ApiKeyRequired"] is True
    assert resources["HealthGetMethod"]["Properties"]["ApiKeyRequired"] is False


def test_usage_plan_throttling(cfn_data):
    plan = cfn_data["Resources"]["ResumeApiUsagePlan"]
    props = plan["Properties"]
    assert "Throttle" in props
    assert "Quota" in props
    assert props["Quota"]["Period"] == "MONTH"
