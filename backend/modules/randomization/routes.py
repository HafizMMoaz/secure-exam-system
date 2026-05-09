from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.randomization.controller import generate, order, health

randomization_bp = Blueprint("randomization_bp", __name__)


@randomization_bp.route("/generate", methods=["POST"])
@jwt_required
@role_required("student")
def generate_route():
    """
    Generate deterministic randomized question order for the authenticated student.
    ---
    tags:
      - Randomization
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
        description: Randomization generated
      400:
        description: Bad request
    """
    return generate()


@randomization_bp.route("/order", methods=["GET"])
@jwt_required
@role_required("student")
def order_route():
    """
    Get previously generated randomized order for the authenticated student.
    ---
    tags:
      - Randomization
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Randomized order returned
      404:
        description: Randomized order not found
    """
    return order()


@randomization_bp.route("/health", methods=["GET"])
def health_route():
    """
    Randomization module health check.
    ---
    tags:
      - Randomization
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
