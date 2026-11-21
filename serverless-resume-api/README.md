# Serverless Resume REST API on AWS

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![AWS-Serverless](https://img.shields.io/badge/AWS-Serverless%20Architecture-orange.svg)](https://aws.amazon.com/serverless/)
[![API-Gateway](https://img.shields.io/badge/Amazon-API%20Gateway-red.svg)](https://aws.amazon.com/api-gateway/)
[![AWS-Lambda](https://img.shields.io/badge/AWS-Lambda%20Functions-FF9900.svg)](https://aws.amazon.com/lambda/)
[![DynamoDB](https://img.shields.io/badge/Amazon-DynamoDB%20NoSQL-4053D6.svg)](https://aws.amazon.com/dynamodb/)
[![Tests](https://img.shields.io/badge/Pytest-24%2F24%20Passed-brightgreen.svg)](https://pytest.org)

A production-grade, cloud-native serverless REST API deployed on AWS that serves structured professional resume data. Built with **Amazon API Gateway**, **AWS Lambda**, and **Amazon DynamoDB**, featuring API Key authentication, Usage Plan throttling, automated Infrastructure as Code (CloudFormation), and an interactive web sandbox.

---

## 1. Cloud-Native Serverless Architecture

```
                                      CLIENT CONSUMER
                                (Web Browser, CLI, or Mobile App)
                                              │
                                              │ HTTP GET with header 'x-api-key'
                                              ▼
                        ┌──────────────────────────────────────────────┐
                        │              Amazon API Gateway              │
                        │               (REST API Regional)            │
                        ├──────────────────────────────────────────────┤
                        │ • Route Ingestion: /resume, /personal, etc.  │
                        │ • API Key Authentication Gatekeeper          │
                        │ • Usage Plan Throttling & Quota:             │
                        │     - Rate Limit : 10 requests / sec         │
                        │     - Burst Limit: 20 requests               │
                        │     - Quota      : 5,000 requests / month    │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               │ AWS_PROXY Lambda Integration
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │               AWS Lambda Backend             │
                        │           (Python 3.11/3.12/3.13)            │
                        ├──────────────────────────────────────────────┤
                        │ • Routing Dispatcher                         │
                        │ • DynamoDB Query Engine                      │
                        │ • Bundled Local JSON Fallback (Zero Cold-Lag)│
                        │ • Automatic CORS Preflight & Headers         │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               │ Single-Table Query (boto3)
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │               Amazon DynamoDB                │
                        │          (ServerlessResumeTable)             │
                        ├──────────────────────────────────────────────┤
                        │ • Billing Mode: PAY_PER_REQUEST              │
                        │ • Partition Key: 'section' (String)          │
                        │ • Sort Key     : 'id' (String)               │
                        │ • Point-in-time recovery & KMS Encryption    │
                        └──────────────────────────────────────────────┘
```

---

## 2. API Endpoints Specification

| Method & Path | Auth Required | Description | Sample Output |
| :--- | :---: | :--- | :--- |
| `GET /resume` | **Yes (`x-api-key`)** | Returns complete aggregated resume document. | Full JSON with all sections |
| `GET /resume/personal` | **Yes (`x-api-key`)** | Personal bio, title, contact, profiles, and summary. | `{ name: "Alex Vance", title: "..." }` |
| `GET /resume/experience` | **Yes (`x-api-key`)** | Work history, roles, companies, achievements. | `[ { role: "Staff Cloud Architect", ... } ]` |
| `GET /resume/education` | **Yes (`x-api-key`)** | Degrees, universities, honors, and coursework. | `[ { degree: "M.S. Computer Science", ... } ]` |
| `GET /resume/skills` | **Yes (`x-api-key`)** | Categorized skills (cloud, languages, devops). | `{ cloud: [...], languages: [...] }` |
| `GET /resume/projects` | **Yes (`x-api-key`)** | Featured engineering portfolio projects. | `[ { name: "Cloud Security IR", ... } ]` |
| `GET /resume/certifications`| **Yes (`x-api-key`)** | Verified certifications (AWS, CKA). | `[ { name: "AWS Solutions Architect", ... } ]` |
| `GET /health` | **None (Public)** | Health check, runtime, and architecture telemetry. | `{ status: "healthy", service: "..." }` |

---

## 3. Directory Structure

```
serverless-resume-api/
├── cli.py                     # Operator CLI (test-endpoint, seed-dynamodb, validate-cfn, list-endpoints)
├── cloudformation/
│   └── template.yaml          # Complete 26-resource CloudFormation / SAM IaC template
├── data/
│   └── resume_data.json       # Master resume data source (structured JSON)
├── src/
│   ├── __init__.py
│   ├── dynamodb_manager.py    # DynamoDB table provisioning, queries, and seeding logic
│   ├── lambda_function.py     # Primary AWS Lambda handler for API Gateway proxy events
│   ├── seed_dynamodb.py       # Standalone DynamoDB data seeder script
│   └── web_app.py             # FastAPI sandbox, API Gateway simulator, and web dashboard
├── static/
│   └── index.html             # Interactive Resume View + API Gateway Sandbox UI
├── tests/
│   ├── test_api_auth.py       # API Key authentication & usage plan throttling tests
│   ├── test_cloudformation.py # CloudFormation syntax, DynamoDB schema, and resource tests
│   ├── test_dynamodb_manager.py # DynamoDB operations and queries using moto mock
│   ├── test_lambda_function.py  # Lambda handler routing, CORS, and response tests
│   └── test_web_app.py        # Web app and API endpoint integration tests
└── README.md
```

---

## 4. DynamoDB Single-Table Data Model

The database utilizes an on-demand DynamoDB table design with composite primary keys:

- **Partition Key (`section`)**: Partitions data by logical resume section.
- **Sort Key (`id`)**: Differentiates items within a section.

| Partition Key (`section`) | Sort Key (`id`) | Item Attributes Summary |
| :--- | :--- | :--- |
| `personal` | `profile` | `name`, `title`, `email`, `phone`, `location`, `website`, `summary` |
| `experience` | `exp-001` | `role`, `company`, `period`, `location`, `description`, `achievements`, `technologies` |
| `experience` | `exp-002` | `role`, `company`, `period`, `location`, `description`, `achievements`, `technologies` |
| `education` | `edu-001` | `degree`, `institution`, `period`, `honors`, `coursework` |
| `skills` | `cloud_and_serverless` | `category`, `skills`: `["AWS Lambda", "API Gateway", "DynamoDB", ...]` |
| `projects` | `proj-001` | `name`, `description`, `technologies`, `link` |
| `certifications` | `cert-001` | `name`, `issuer`, `date`, `badge_id` |

---

## 5. Security Controls: API Keys & Usage Plans

1. **Authentication Gatekeeper**:
   - Every `/resume*` method in API Gateway is configured with `ApiKeyRequired: true`.
   - Requests omitting `x-api-key` are blocked at the API Gateway layer with `403 Forbidden` (`ForbiddenException`), preventing unauthenticated compute costs.
2. **Throttling & Rate Limiting**:
   - **Steady-State Rate**: 10 requests per second.
   - **Burst Capacity**: 20 requests.
   - Prevents DoS attacks and runaway consumption.
3. **Monthly Quota**:
   - **Limit**: 5,000 requests per month.
   - Requests exceeding quota receive `429 Too Many Requests`.

---

## 6. Quickstart & CLI Commands

### 1. Prerequisites & Dependencies
```bash
pip install boto3 pyyaml moto fastapi uvicorn pydantic pytest httpx
```

### 2. Validate CloudFormation Template
```bash
python cli.py validate-cfn
```
**Output:**
```text
[*] Validating CloudFormation Template: cloudformation/template.yaml
[+] Template successfully parsed as valid YAML!
    Resources: 26
      • ServerlessResumeTable (AWS::DynamoDB::Table)
      • ResumeLambdaExecutionRole (AWS::IAM::Role)
      • ResumeApiFunction (AWS::Lambda::Function)
      • ResumeRestApi (AWS::ApiGateway::RestApi)
      • ResumeApiKey (AWS::ApiGateway::ApiKey)
      • ResumeApiUsagePlan (AWS::ApiGateway::UsagePlan)
      • ResumeApiUsagePlanKey (AWS::ApiGateway::UsagePlanKey)
      ...
    Outputs  : 6
[+] CloudFormation template structure verified successfully.
```

### 3. Test Endpoints Locally with API Key
```bash
# Authenticated request with valid key
python cli.py test-endpoint --path /resume/personal --api-key res-api-key-live-98213-alex-vance

# Test unauthenticated request (403 Forbidden)
python cli.py test-endpoint --path /resume/personal --api-key invalid-key
```

### 4. Seed Simulated DynamoDB Table
```bash
python cli.py seed-dynamodb
```

---

## 7. Running the Interactive Web Sandbox

Launch the local web dashboard and API sandbox:
```bash
python -m uvicorn src.web_app:app --host 127.0.0.1 --port 8000 --reload
```
Navigate to **`http://127.0.0.1:8000/`** to:
1. View the styled resume rendered directly from the API.
2. Test API Gateway responses with valid, missing, or invalid API keys.
3. Observe rate-limiting response headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`).
4. Inspect DynamoDB records and view the CloudFormation template.

---

## 8. Automated Test Suite Verification

```text
============================= test session starts =============================
platform win32 -- Python 3.13.18, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\KAUSHIK
plugins: anyio-4.16.0
collected 24 items

tests/test_api_auth.py::test_resume_endpoint_without_api_key_forbidden PASSED [  4%]
tests/test_api_auth.py::test_resume_endpoint_with_invalid_api_key_forbidden PASSED [  8%]
tests/test_api_auth.py::test_resume_endpoint_with_valid_api_key_success PASSED [ 12%]
tests/test_api_auth.py::test_health_endpoint_without_api_key_success PASSED [ 16%]
tests/test_cloudformation.py::test_cfn_structure PASSED               [ 20%]
tests/test_cloudformation.py::test_cfn_core_resources PASSED          [ 25%]
tests/test_cloudformation.py::test_dynamodb_schema PASSED             [ 29%]
tests/test_cloudformation.py::test_api_gateway_api_key_required PASSED [ 33%]
tests/test_cloudformation.py::test_usage_plan_throttling PASSED       [ 37%]
tests/test_dynamodb_manager.py::test_create_and_seed_dynamodb PASSED  [ 41%]
tests/test_lambda_function.py::test_health_check_endpoint PASSED      [ 45%]
tests/test_lambda_function.py::test_resume_full_endpoint PASSED       [ 50%]
tests/test_lambda_function.py::test_resume_personal_endpoint PASSED   [ 54%]
tests/test_lambda_function.py::test_resume_experience_endpoint PASSED [ 58%]
tests/test_lambda_function.py::test_resume_education_endpoint PASSED  [ 62%]
tests/test_lambda_function.py::test_resume_skills_endpoint PASSED     [ 66%]
tests/test_lambda_function.py::test_cors_preflight_options PASSED     [ 70%]
tests/test_lambda_function.py::test_method_not_allowed_post PASSED    [ 75%]
tests/test_lambda_function.py::test_not_found_invalid_path PASSED     [ 79%]
tests/test_web_app.py::test_health PASSED                             [ 83%]
tests/test_web_app.py::test_get_resume_endpoint PASSED                [ 87%]
tests/test_web_app.py::test_get_resume_section_endpoint PASSED        [ 91%]
tests/test_web_app.py::test_get_cloudformation_yaml PASSED           [ 95%]
tests/test_web_app.py::test_seed_dynamodb_endpoint PASSED            [100%]

======================= 24 passed in 22.82s ========================
```

---

## License & Author
Engineered for serverless cloud architecture research and cloud developer certification standards. Adheres to AWS Well-Architected Serverless Applications Lens.
