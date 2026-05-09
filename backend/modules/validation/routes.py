from flask import Blueprint

from middleware.jwt_auth import jwt_required
from modules.validation.controller import check, sanitize, health

validation_bp = Blueprint("validation_bp", __name__)


@validation_bp.route("/check", methods=["POST"])
@jwt_required
def check_route():
    """
    Validate arbitrary JSON input against injection and size constraints.
    ---
    tags:
      - Validation
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
    responses:
      200:
        description: Validation result
    """
    return check()


@validation_bp.route("/sanitize", methods=["POST"])
@jwt_required
def sanitize_route():
    """
    Validate a single text field for safe downstream use.
    ---
    tags:
      - Validation
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - text
          properties:
            text:
              type: string
    responses:
      200:
        description: Sanitization result
      400:
        description: Bad request
    """
    return sanitize()


@validation_bp.route("/health", methods=["GET"])
def health_route():
    """
    Validation module health check.
    ---
    tags:
      - Validation
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
