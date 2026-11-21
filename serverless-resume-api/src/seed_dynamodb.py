"""
DynamoDB Seeder Script for Serverless Resume API
Initializes the DynamoDB table and loads data from data/resume_data.json.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.dynamodb_manager import DynamoDBManager


def seed():
    json_path = os.path.join(PROJECT_ROOT, "data", "resume_data.json")
    if not os.path.exists(json_path):
        print(f"[-] Data file not found: {json_path}")
        sys.exit(1)

    print(f"[*] Initializing DynamoDB Manager...")
    mgr = DynamoDBManager()

    print(f"[*] Ensuring DynamoDB table '{mgr.table_name}' exists...")
    mgr.create_table_if_not_exists()

    print(f"[*] Seeding data from {json_path}...")
    count = mgr.seed_from_json(json_path)
    print(f"[+] Successfully seeded {count} items into DynamoDB table '{mgr.table_name}'!")


if __name__ == "__main__":
    seed()
