from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.logging.controller import write, verify, verify_window_route, list_entries, health

logging_bp = Blueprint("logging_bp", __name__)


@logging_bp.route("/write", methods=["POST"])
def write_route():
    """
    Record a log entry.
    ---
    tags:
      - Logging
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - module
            - level
            - user_id
            - action
            - timestamp
          properties:
            module:
              type: string
              example: Module_13_Logging
            level:
              type: string
              example: INFO
            user_id:
              type: string
              example: 64abc123
            exam_id:
              type: string
              example: 64exam123
            action:
              type: string
              example: user_login
            details:
              type: object
              example: {"ip": "1.2.3.4"}
            timestamp:
              type: string
              example: 2026-05-03T10:00:00Z
    responses:
      202:
        description: Log accepted for processing
      400:
        description: Missing or invalid parameters
    """
    return write()


@logging_bp.route("/verify/<log_id>", methods=["GET"])
@jwt_required
@role_required("teacher")
def verify_route(log_id):
    """
    Verify a log entry's integrity.
    ---
    tags:
      - Logging
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: log_id
        type: string
        required: true
    responses:
      200:
        description: Verification result
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
      404:
        description: Log entry not found
    """
    return verify(log_id)


@logging_bp.route("/verify", methods=["GET"])
@jwt_required
@role_required("teacher")
def verify_window_bp_route():
    """
    Verify integrity of a window of log entries - recomputes SHA-256 over each
    log document and reports any that fail. Demonstrates the section 27.3 integrity
    guarantee against direct DB tampering.
    ---
    tags:
      - Logging
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: user_id
        type: string
      - in: query
        name: exam_id
        type: string
      - in: query
        name: level
        type: string
      - in: query
        name: module
        type: string
      - in: query
        name: limit
        type: integer
        default: 500
    responses:
      200:
        description: Verification summary
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return verify_window_route()


@logging_bp.route("/list", methods=["GET"])
@jwt_required
@role_required("teacher")
def list_route():
    """
    List log entries with optional filters.
    ---
    tags:
      - Logging
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: user_id
        type: string
      - in: query
        name: exam_id
        type: string
      - in: query
        name: level
        type: string
      - in: query
        name: module
        type: string
    responses:
      200:
        description: Logs returned successfully
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return list_entries()


@logging_bp.route("/health", methods=["GET"])
def health_route():
    """
    Logging module health check.
    ---
    tags:
      - Logging
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
