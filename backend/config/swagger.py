"""
Swagger / OpenAPI setup using Flasgger.

Install:
    pip install flasgger

Usage in app.py:
    from config.swagger import init_swagger
    init_swagger(app)

Then access docs at:
    http://localhost:5000/api/docs
"""

from flasgger import Swagger

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/api/docs/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
}

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "Secure Online Examination System",
        "description": (
            "IS-Lab Semester Project — Multi-layer security & behavioral risk detection. "
            "All protected endpoints require a Bearer JWT token in the Authorization header."
        ),
        "version": "1.0.0",
        "contact": {
            "name": "IS-Lab Group"
        }
    },
    "basePath": "/",
    "schemes": ["http"],
    "securityDefinitions": {
        "BearerAuth": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter the token with the Bearer prefix: **Bearer &lt;your_jwt_token&gt;**"
        }
    },
    # Applied globally — every endpoint requires JWT unless overridden
    "security": [{"BearerAuth": []}],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    # ── Reusable response schemas ──────────────────────────────────────────────
    "definitions": {
        "SuccessResponse": {
            "type": "object",
            "properties": {
                "status":  {"type": "string", "example": "success"},
                "data":    {"type": "object"},
                "message": {"type": "string", "example": "Request processed successfully"}
            }
        },
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "status":     {"type": "string", "example": "error"},
                "error_code": {"type": "integer", "example": 401},
                "message":    {"type": "string", "example": "JWT expired"},
                "timestamp":  {"type": "string", "example": "2024-01-15T10:30:00Z"}
            }
        },
        "HealthResponse": {
            "type": "object",
            "properties": {
                "module":       {"type": "string", "example": "Module_1_Auth"},
                "status":       {"type": "string", "example": "healthy"},
                "dependencies": {"type": "array", "items": {"type": "string"}},
                "version":      {"type": "string", "example": "1.0.0"}
            }
        },
        "RiskDataEntry": {
            "type": "object",
            "properties": {
                "user_id":   {"type": "string"},
                "exam_id":   {"type": "string"},
                "timestamp": {"type": "string", "example": "2024-01-15T10:30:00Z"},
                "metric":    {"type": "string", "example": "tab_switch_count"},
                "value":     {"type": "number", "example": 3}
            }
        },
        "RiskDataResponse": {
            "type": "object",
            "properties": {
                "module": {"type": "string"},
                "data": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/RiskDataEntry"}
                }
            }
        },
        # ── Common error responses (referenced in each route) ──────────────────
        "Error400": {"$ref": "#/definitions/ErrorResponse"},
        "Error401": {"$ref": "#/definitions/ErrorResponse"},
        "Error403": {"$ref": "#/definitions/ErrorResponse"},
        "Error404": {"$ref": "#/definitions/ErrorResponse"},
        "Error409": {"$ref": "#/definitions/ErrorResponse"},
        "Error500": {"$ref": "#/definitions/ErrorResponse"},
        "Error503": {"$ref": "#/definitions/ErrorResponse"},
    },
    # ── Tags — one per module ──────────────────────────────────────────────────
    "tags": [
        {"name": "Health",         "description": "System-wide health check"},
        {"name": "Auth",           "description": "Module 1 — Secure Authentication"},
        {"name": "Session",        "description": "Module 2 — Secure Session Management"},
        {"name": "Device",         "description": "Module 3 — Device Fingerprinting"},
        {"name": "Activation",     "description": "Module 4 — Activation Code Security"},
        {"name": "RBAC",           "description": "Module 5 — Role-Based Access Control"},
        {"name": "Questions",      "description": "Module 6 — Secure Question Delivery"},
        {"name": "Randomization",  "description": "Module 7 — Question Randomization"},
        {"name": "Timer",          "description": "Module 8 — Secure Timer"},
        {"name": "Validation",     "description": "Module 9 — Input Validation"},
        {"name": "Tab",            "description": "Module 10 — Tab Monitoring"},
        {"name": "Clipboard",      "description": "Module 11 — Clipboard Monitoring"},
        {"name": "Activity",       "description": "Module 12 — Activity Logging"},
        {"name": "Logging",        "description": "Module 13 — Secure Logging Gateway"},
        {"name": "MultiSession",   "description": "Module 14 — Multi-Session Detection"},
        {"name": "Behavioral",     "description": "Module 15 — Behavioral Analysis"},
        {"name": "Similarity",     "description": "Module 16 — Answer Similarity Detection"},
        {"name": "Risk",           "description": "Module 17 — Risk Scoring & Dashboard"},
    ]
}


def init_swagger(app):
    """Call this in app.py after creating the Flask app."""
    Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)