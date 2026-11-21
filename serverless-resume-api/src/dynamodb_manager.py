"""
DynamoDB Manager Module for Serverless Resume API
Handles table provisioning, seeding from JSON, and querying by section and item ID.
"""

import json
import logging
import os
from decimal import Decimal
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
logger = logging.getLogger("resume_api.dynamodb")
logger.setLevel(logging.INFO)

DEFAULT_TABLE_NAME = "ServerlessResumeTable"


class DecimalEncoder(json.JSONEncoder):
    """Helper to convert DynamoDB Decimal types to standard JSON numbers/floats."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


class DynamoDBManager:
    """
    Encapsulates Amazon DynamoDB operations for resume storage.
    Schema:
      - Partition Key: section (String)
      - Sort Key: id (String)
    """

    def __init__(self, dynamodb_resource: Optional[Any] = None, table_name: Optional[str] = None):
        region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self.dynamodb = dynamodb_resource or boto3.resource("dynamodb", region_name=region)
        self.table_name = table_name or os.environ.get("TABLE_NAME", DEFAULT_TABLE_NAME)
        self._table = None

    @property
    def table(self):
        if self._table is None:
            self._table = self.dynamodb.Table(self.table_name)
        return self._table

    def create_table_if_not_exists(self) -> Any:
        """Create the DynamoDB table with on-demand (PAY_PER_REQUEST) capacity."""
        client = self.dynamodb.meta.client if hasattr(self.dynamodb, "meta") else boto3.client("dynamodb")
        try:
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {"AttributeName": "section", "KeyType": "HASH"},  # Partition Key
                    {"AttributeName": "id", "KeyType": "RANGE"}       # Sort Key
                ],
                AttributeDefinitions=[
                    {"AttributeName": "section", "AttributeType": "S"},
                    {"AttributeName": "id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST"
            )
            table.wait_until_exists()
            logger.info("Created DynamoDB table: %s", self.table_name)
            self._table = table
            return table
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                logger.info("Table %s already exists.", self.table_name)
                return self.table
            raise e

    def seed_from_json(self, data_or_path: Dict[str, Any] | str) -> int:
        """
        Populate DynamoDB table from resume JSON structure.
        Returns total number of items inserted.
        """
        if isinstance(data_or_path, str):
            with open(data_or_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = data_or_path

        items_to_put = []

        # 1. Personal section
        if "personal" in data:
            item = {"section": "personal", "id": "profile", **data["personal"]}
            items_to_put.append(item)

        # 2. Experience section (list of jobs)
        if "experience" in data:
            for job in data["experience"]:
                item = {"section": "experience", "id": job["id"], **job}
                items_to_put.append(item)

        # 3. Education section (list of degrees)
        if "education" in data:
            for edu in data["education"]:
                item = {"section": "education", "id": edu["id"], **edu}
                items_to_put.append(item)

        # 4. Skills section (categorized dict)
        if "skills" in data:
            for cat, skills_list in data["skills"].items():
                item = {"section": "skills", "id": cat, "category": cat, "skills": skills_list}
                items_to_put.append(item)

        # 5. Projects section (list)
        if "projects" in data:
            for proj in data["projects"]:
                item = {"section": "projects", "id": proj["id"], **proj}
                items_to_put.append(item)

        # 6. Certifications section (list)
        if "certifications" in data:
            for cert in data["certifications"]:
                item = {"section": "certifications", "id": cert["id"], **cert}
                items_to_put.append(item)

        # 7. Metadata section
        if "metadata" in data:
            item = {"section": "metadata", "id": "info", **data["metadata"]}
            items_to_put.append(item)

        # Batch write items
        with self.table.batch_writer() as batch:
            for item in items_to_put:
                batch.put_item(Item=item)

        logger.info("Seeded %d items into DynamoDB table %s", len(items_to_put), self.table_name)
        return len(items_to_put)

    def get_section(self, section: str) -> Any:
        """
        Query all items in a given section.
        """
        try:
            from boto3.dynamodb.conditions import Key
            res = self.table.query(
                KeyConditionExpression=Key("section").eq(section)
            )
            items = res.get("Items", [])
            if not items:
                return None

            # Reconstruct original structure
            if section == "personal":
                # Strip DynamoDB partition/sort keys for clean API response
                clean = {k: v for k, v in items[0].items() if k not in ["section", "id"]}
                return clean

            elif section in ["experience", "education", "projects", "certifications"]:
                clean_list = []
                for it in items:
                    clean = {k: v for k, v in it.items() if k != "section"}
                    clean_list.append(clean)
                return clean_list

            elif section == "skills":
                clean_dict = {}
                for it in items:
                    cat = it.get("category", it.get("id"))
                    clean_dict[cat] = it.get("skills", [])
                return clean_dict

            elif section == "metadata":
                clean = {k: v for k, v in items[0].items() if k not in ["section", "id"]}
                return clean

            return items
        except Exception as e:
            logger.warning("DynamoDB query failed for section %s: %s", section, e)
            return None

    def get_full_resume(self) -> Dict[str, Any]:
        """Reconstruct entire resume object from all DynamoDB sections."""
        sections = ["personal", "experience", "education", "skills", "projects", "certifications", "metadata"]
        full_doc = {}
        for sec in sections:
            val = self.get_section(sec)
            if val is not None:
                full_doc[sec] = val
        return full_doc
