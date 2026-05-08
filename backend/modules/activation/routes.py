from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.activation.controller import generate, validate, status, health

activation_bp = Blueprint("activation_bp", __name__)


@activation_bp.route("/generate", methods=["POST"])
@jwt_required
@role_required("teacher")
def generate_route():
    """
    Generate a one-time activation code for a teacher-approved exam.
    ---
    tags:
      - Activation
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - exam_id
          properties:
            exam_id:
              type: string
    responses:
      200:
        description: Activation code generated
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return generate()


@activation_bp.route("/validate", methods=["POST"])
@jwt_required
@role_required("student")
def validate_route():
    """
    Validate a student activation code and activate the exam.
    ---
    tags:
      - Activation
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - exam_id
            - code
          properties:
            exam_id:
              type: string
            code:
              type: string
    responses:
      200:
        description: Activation code validated
      400:
        description: Invalid activation code or expired code
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return validate()


@activation_bp.route("/status/<exam_id>", methods=["GET"])
@jwt_required
@role_required("teacher")
def status_route(exam_id):
    """
    Get the latest activation code status for an exam.
    ---
    tags:
      - Activation
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        required: true
        type: string
    responses:
      200:
        description: Activation code status returned
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
      404:
        description: No activation code found
    """
    return status(exam_id)


@activation_bp.route("/health", methods=["GET"])
def health_route():
    """
    Activation module health check.
    ---
    tags:
      - Activation
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
