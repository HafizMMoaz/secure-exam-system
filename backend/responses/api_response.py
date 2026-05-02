from flask import jsonify
from datetime import datetime, timezone


def success_response(data=None, message="Request processed successfully", status_code=200):
    """
    Standard success response format.
    
    Returns:
        {
            "status": "success",
            "data": {},
            "message": ""
        }
    """
    response = {
        "status": "success",
        "data": data if data is not None else {},
        "message": message
    }
    return jsonify(response), status_code


def error_response(message, error_code, status_code=None):
    """
    Standard error response format.

    Returns:
        {
            "status": "error",
            "error_code": 401,
            "message": "...",
            "timestamp": "ISO8601"
        }
    """
    if status_code is None:
        status_code = error_code

    response = {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    return jsonify(response), status_code


def accepted_response(message="Request accepted"):
    """
    HTTP 202 Accepted — used by logging gateway (async).
    """
    response = {
        "status": "accepted",
        "data": {},
        "message": message
    }
    return jsonify(response), 202


def health_response(module_name, dependencies=None, version="1.0.0", healthy=True):
    """
    Standard health check response for all modules.

    Returns:
        {
            "module": "Module_1_Auth",
            "status": "healthy" | "unhealthy",
            "dependencies": ["mongodb"],
            "version": "1.0.0"
        }
    """
    response = {
        "module": module_name,
        "status": "healthy" if healthy else "unhealthy",
        "dependencies": dependencies if dependencies is not None else ["mongodb"],
        "version": version
    }
    status_code = 200 if healthy else 503
    return jsonify(response), status_code


def risk_data_response(module_name, data=None):
    """
    Standard risk data response required by Module 17 aggregation.

    Returns:
        {
            "module": "Module_15_Behavioral",
            "data": [ { user_id, exam_id, timestamp, metric, value } ]
        }
    """
    response = {
        "module": module_name,
        "data": data if data is not None else []
    }
    return jsonify(response), 200