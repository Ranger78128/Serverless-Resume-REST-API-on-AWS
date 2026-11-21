"""
FastAPI Serverless Resume API Sandbox & Web Dashboard
Provides REST API endpoints, API Gateway simulation with x-api-key authentication,
DynamoDB inspection, and interactive resume visualization.
"""

import json
import logging
import os
import sys
import time
from typing import Dict, Any, Optional

import boto3
import moto
from fastapi import FastAPI, HTTPException, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.lambda_function import lambda_handler
from src.dynamodb_manager import DynamoDBManager

app = FastAPI(
    title="Serverless Resume API on AWS",
    version="1.0.0",
    description="Production-ready serverless REST API backed by AWS Lambda, Amazon API Gateway, and Amazon DynamoDB"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

DEMO_API_KEY = "res-api-key-live-98213-alex-vance"


class InvokeLambdaRequest(BaseModel):
    path: str = Field(..., description="API endpoint path (e.g., /resume/personal)")
    http_method: str = Field("GET", description="HTTP Method")
    api_key: Optional[str] = Field(None, description="API Key for x-api-key header")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Serverless Resume API running. static/index.html not found.</h1>")


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "Serverless Resume API",
        "architecture": "Amazon API Gateway -> AWS Lambda -> Amazon DynamoDB",
        "timestamp": time.time()
    }


@app.get("/api/resume")
async def get_resume(x_api_key: Optional[str] = Header(None)):
    """Simulates API Gateway /resume endpoint with API Key requirement."""
    event = {
        "httpMethod": "GET",
        "path": "/resume",
        "headers": {"x-api-key": x_api_key} if x_api_key else {}
    }
    res = lambda_handler(event, None)
    return JSONResponse(status_code=res["statusCode"], content=json.loads(res["body"]))


@app.get("/api/resume/{section}")
async def get_resume_section(section: str, x_api_key: Optional[str] = Header(None)):
    """Simulates API Gateway /resume/{section} endpoint."""
    event = {
        "httpMethod": "GET",
        "path": f"/resume/{section}",
        "headers": {"x-api-key": x_api_key} if x_api_key else {}
    }
    res = lambda_handler(event, None)
    return JSONResponse(status_code=res["statusCode"], content=json.loads(res["body"]))


@app.post("/api/simulate-apigateway")
async def simulate_api_gateway(req: InvokeLambdaRequest):
    """
    Simulates Amazon API Gateway behavior:
    1. Evaluates API Key requirement on /resume* endpoints.
    2. Simulates Usage Plan rate limiting headers (X-RateLimit-Limit, X-RateLimit-Remaining).
    3. Invokes the AWS Lambda function with API Gateway proxy payload.
    """
    path = req.path.strip()
    if not path.startswith("/"):
        path = "/" + path

    # API Gateway security check: all /resume endpoints require API Key
    if path.startswith("/resume"):
        if not req.api_key:
            return JSONResponse(
                status_code=403,
                content={
                    "message": "Forbidden",
                    "error": "Missing Authentication Token or Invalid API Key (x-api-key required by Usage Plan)",
                    "tip": f"Supply header 'x-api-key: {DEMO_API_KEY}' to authenticate."
                },
                headers={
                    "x-amzn-errortype": "ForbiddenException"
                }
            )
        elif req.api_key != DEMO_API_KEY and req.api_key != "valid-test-key":
            return JSONResponse(
                status_code=403,
                content={
                    "message": "Forbidden",
                    "error": "Invalid API Key. Not recognized by API Gateway Usage Plan."
                },
                headers={
                    "x-amzn-errortype": "ForbiddenException"
                }
            )

    start_time = time.time()
    event = {
        "httpMethod": req.http_method,
        "path": path,
        "headers": {
            "x-api-key": req.api_key,
            "User-Agent": "FastAPI-APIGateway-Simulator"
        },
        "requestContext": {
            "identity": {"apiKeyId": "key-demo-001"},
            "stage": "Prod",
            "requestId": f"req-{int(time.time()*1000)}"
        }
    }

    lambda_resp = lambda_handler(event, None)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    return JSONResponse(
        status_code=lambda_resp["statusCode"],
        content=json.loads(lambda_resp["body"]),
        headers={
            "X-Amzn-RequestId": event["requestContext"]["requestId"],
            "X-RateLimit-Limit": "10",
            "X-RateLimit-Remaining": "9",
            "X-Burst-Limit": "20",
            "X-Latency-Ms": str(duration_ms)
        }
    )


@app.post("/api/seed-dynamodb")
async def seed_dynamodb():
    """Seed DynamoDB table using moto mock."""
    try:
        with moto.mock_aws():
            mgr = DynamoDBManager()
            mgr.create_table_if_not_exists()
            data_file = os.path.join(PROJECT_ROOT, "data", "resume_data.json")
            count = mgr.seed_from_json(data_file)
            items = mgr.get_full_resume()
            return {
                "status": "success",
                "message": f"Successfully seeded {count} items into DynamoDB",
                "table_name": mgr.table_name,
                "sections_seeded": list(items.keys())
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB seeding error: {str(e)}")


@app.get("/api/cloudformation")
async def get_cloudformation():
    """Retrieve CloudFormation template content."""
    cfn_path = os.path.join(PROJECT_ROOT, "cloudformation", "template.yaml")
    if not os.path.exists(cfn_path):
        raise HTTPException(status_code=404, detail="Template not found")
    with open(cfn_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"yaml_content": content}
