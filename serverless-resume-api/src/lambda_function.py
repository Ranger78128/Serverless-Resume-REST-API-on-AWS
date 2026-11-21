"""
AWS Lambda Serverless Resume API Backend Handler
Routes incoming Amazon API Gateway proxy requests, queries DynamoDB with
automatic fallback to local JSON, enforces CORS, and formats responses.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
logger = logging.getLogger("resume_api.handler")
logger.setLevel(logging.INFO)

# Local fallback data path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(CURRENT_DIR, "..", "data", "resume_data.json")

# Lazy-loaded local JSON cache
_LOCAL_RESUME_DATA: Optional[Dict[str, Any]] = None


def load_local_resume_data() -> Dict[str, Any]:
    """Load resume data from bundled JSON file."""
    global _LOCAL_RESUME_DATA
    if _LOCAL_RESUME_DATA is None:
        path = DATA_FILE_PATH
        # Also check current working directory or relative to Lambda package root
        if not os.path.exists(path):
            path = os.path.join(CURRENT_DIR, "resume_data.json")
        if not os.path.exists(path):
            path = os.path.join("data", "resume_data.json")

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                _LOCAL_RESUME_DATA = json.load(f)
            logger.info("Loaded resume data from local file: %s", path)
        else:
            logger.error("Could not locate resume_data.json at %s", path)
            _LOCAL_RESUME_DATA = {}
    return _LOCAL_RESUME_DATA


def build_response(status_code: int, body_data: Any, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Format RFC-compliant API Gateway proxy response with CORS headers."""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Amz-Date, Authorization, X-Api-Key, x-api-key",
        "Cache-Control": "max-age=300, s-maxage=600"
    }
    if extra_headers:
        headers.update(extra_headers)

    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body_data, indent=2)
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Primary AWS Lambda Entrypoint for Amazon API Gateway Proxy Integration.
    """
    logger.info("Received event: %s", json.dumps(event.get("path", "")))

    # Handle CORS preflight
    http_method = event.get("httpMethod", "GET").upper()
    if http_method == "OPTIONS":
        return build_response(200, {"message": "CORS preflight OK"})

    if http_method != "GET":
        return build_response(405, {"error": "Method Not Allowed", "allowed": ["GET", "OPTIONS"]})

    # Normalize path (handle API Gateway stage prefixes like /Prod/resume -> /resume)
    raw_path = event.get("path", "/").strip()
    path = raw_path.lower()
    for prefix in ["/prod", "/stage", "/dev", "/v1"]:
        if path.startswith(prefix):
            path = path[len(prefix):]
    if not path.startswith("/"):
        path = "/" + path
    path = path.rstrip("/") or "/"

    # 1. Health check endpoint (unauthenticated)
    if path in ["/health", "/ping"]:
        return build_response(200, {
            "status": "healthy",
            "service": "Serverless Resume REST API",
            "runtime": "AWS Lambda (Python 3.13)",
            "database": "Amazon DynamoDB (ServerlessResumeTable)"
        })

    # 2. Routing logic for resume sections
    # Determine requested section
    route_map = {
        "/resume": "all",
        "/resume/personal": "personal",
        "/resume/experience": "experience",
        "/resume/education": "education",
        "/resume/skills": "skills",
        "/resume/projects": "projects",
        "/resume/certifications": "certifications",
        "/resume/metadata": "metadata"
    }

    target_section = route_map.get(path)
    if not target_section:
        return build_response(404, {
            "error": "Not Found",
            "requested_path": raw_path,
            "available_endpoints": [
                "GET /resume",
                "GET /resume/personal",
                "GET /resume/experience",
                "GET /resume/education",
                "GET /resume/skills",
                "GET /resume/projects",
                "GET /resume/certifications",
                "GET /health"
            ]
        })

    # 3. Retrieve Data (DynamoDB primary with Local JSON fallback)
    data = None
    data_source = "LocalJSON"

    try:
        from src.dynamodb_manager import DynamoDBManager
        db_mgr = DynamoDBManager()
        if target_section == "all":
            dynamo_data = db_mgr.get_full_resume()
            if dynamo_data and len(dynamo_data) > 0:
                data = dynamo_data
                data_source = "AmazonDynamoDB"
        else:
            section_data = db_mgr.get_section(target_section)
            if section_data is not None:
                data = section_data
                data_source = "AmazonDynamoDB"
    except Exception as e:
        logger.warning("DynamoDB retrieval notice: %s. Using local JSON fallback.", e)

    # Fallback to local JSON if DynamoDB was empty or unavailable
    if data is None:
        local_doc = load_local_resume_data()
        if target_section == "all":
            data = local_doc
        else:
            data = local_doc.get(target_section)
        data_source = "LocalJSON"

    if data is None:
        return build_response(404, {
            "error": f"Section '{target_section}' not found in resume repository."
        })

    response_payload = {
        "status": "success",
        "section": target_section,
        "source": data_source,
        "data": data
    }

    return build_response(200, response_payload)
