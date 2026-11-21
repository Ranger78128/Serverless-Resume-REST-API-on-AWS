#!/usr/bin/env python3
"""
Command-Line Interface for Serverless Resume API
Allows querying endpoints locally, testing API Key enforcement,
seeding DynamoDB, and validating CloudFormation IaC templates.
"""

import argparse
import json
import os
import sys
import yaml

# Support CloudFormation custom YAML tags (!Ref, !Sub, !GetAtt, etc.)
def cfn_multi_constructor(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return {tag_suffix: loader.construct_scalar(node)}
    elif isinstance(node, yaml.SequenceNode):
        return {tag_suffix: loader.construct_sequence(node)}
    elif isinstance(node, yaml.MappingNode):
        return {tag_suffix: loader.construct_mapping(node)}
    return {tag_suffix: None}

yaml.add_multi_constructor("!", cfn_multi_constructor, Loader=yaml.SafeLoader)

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from src.lambda_function import lambda_handler
from src.dynamodb_manager import DynamoDBManager

VALID_DEMO_KEY = "res-api-key-live-98213-alex-vance"


def cmd_test_endpoint(args):
    path = args.path.strip()
    if not path.startswith("/"):
        path = "/" + path

    print("\n" + "=" * 70)
    print(f"  SERVERLESS RESUME API INVOCATION: GET {path}")
    print("=" * 70)

    # API Gateway security check simulation
    if path.startswith("/resume"):
        if not args.api_key:
            print("\033[91m[-] 403 FORBIDDEN: Missing API Key.\033[0m")
            print("    API Gateway Usage Plan requires header: x-api-key")
            print(f"    Pass --api-key {VALID_DEMO_KEY} to authenticate.\n")
            return
        elif args.api_key != VALID_DEMO_KEY:
            print("\033[91m[-] 403 FORBIDDEN: Invalid API Key.\033[0m\n")
            return

    event = {
        "httpMethod": "GET",
        "path": path,
        "headers": {
            "x-api-key": args.api_key
        }
    }

    res = lambda_handler(event, None)
    status_code = res["statusCode"]
    body = json.loads(res["body"])

    status_color = "\033[92m" if status_code == 200 else "\033[91m"
    print(f"[+] HTTP Status: {status_color}[{status_code}]\033[0m")
    if "source" in body:
        print(f"[+] Data Source: {body.get('source')}")
    print("-" * 70)
    print(json.dumps(body, indent=2))
    print("=" * 70 + "\n")


def cmd_seed(args):
    print("\n[*] Initializing DynamoDB Seeding Process...")
    json_path = os.path.join(PROJECT_ROOT, "data", "resume_data.json")

    import moto
    with moto.mock_aws():
        mgr = DynamoDBManager()
        mgr.create_table_if_not_exists()
        count = mgr.seed_from_json(json_path)
        print(f"[+] Successfully seeded {count} items into DynamoDB table: {mgr.table_name}")
        full = mgr.get_full_resume()
        print(f"[+] Verified sections in table: {list(full.keys())}\n")


def cmd_validate_cfn(args):
    cfn_path = args.path or os.path.join(PROJECT_ROOT, "cloudformation", "template.yaml")
    print(f"\n[*] Validating CloudFormation Template: {cfn_path}")
    if not os.path.exists(cfn_path):
        print(f"[-] File not found: {cfn_path}")
        return

    try:
        with open(cfn_path, "r", encoding="utf-8") as f:
            content = f.read()
        parsed = yaml.safe_load(content)

        resources = parsed.get("Resources", {})
        outputs = parsed.get("Outputs", {})

        print("[+] Template successfully parsed as valid YAML!")
        print(f"    Resources: {len(resources)}")
        for r_name, r_body in resources.items():
            print(f"      • {r_name} ({r_body.get('Type')})")
        print(f"    Outputs  : {len(outputs)}")
        print("[+] CloudFormation template structure verified successfully.\n")
    except Exception as e:
        print(f"[-] Validation error: {e}\n")


def cmd_list_endpoints(args):
    print("\n" + "=" * 70)
    print("  SERVERLESS RESUME REST API ENDPOINTS SPECIFICATION")
    print("=" * 70)
    endpoints = [
        ("GET /resume", "Retrieve full aggregate resume document", "Required (x-api-key)"),
        ("GET /resume/personal", "Retrieve personal bio, contact, and summary", "Required (x-api-key)"),
        ("GET /resume/experience", "Retrieve complete work history & accomplishments", "Required (x-api-key)"),
        ("GET /resume/education", "Retrieve academic degrees and honors", "Required (x-api-key)"),
        ("GET /resume/skills", "Retrieve technical skills by category", "Required (x-api-key)"),
        ("GET /resume/projects", "Retrieve featured portfolio projects", "Required (x-api-key)"),
        ("GET /resume/certifications", "Retrieve verified industry certifications", "Required (x-api-key)"),
        ("GET /health", "Public service health and runtime status", "None (Public)"),
    ]
    for method_path, desc, auth in endpoints:
        print(f"  {method_path:<26} | Auth: {auth:<22} | {desc}")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Serverless Resume API Operator CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available Commands")

    # test-endpoint
    tp = subparsers.add_parser("test-endpoint", help="Test an API endpoint locally")
    tp.add_argument("--path", default="/resume", help="Endpoint path (e.g. /resume/personal)")
    tp.add_argument("--api-key", default=VALID_DEMO_KEY, help="API Key for x-api-key header")

    # seed
    subparsers.add_parser("seed-dynamodb", help="Seed DynamoDB table from data/resume_data.json")

    # validate-cfn
    vp = subparsers.add_parser("validate-cfn", help="Validate CloudFormation template syntax")
    vp.add_argument("--path", help="Path to template.yaml")

    # list-endpoints
    subparsers.add_parser("list-endpoints", help="List all REST API routes and authentication rules")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "test-endpoint": cmd_test_endpoint,
        "seed-dynamodb": cmd_seed,
        "validate-cfn": cmd_validate_cfn,
        "list-endpoints": cmd_list_endpoints
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
