from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.rbac.controller import permissions, check, users, toggle, health

rbac_bp = Blueprint("rbac_bp", __name__)


@rbac_bp.route("/permissions", methods=["GET"])
@jwt_required
def permissions_route():
    """
    Get the permission list for the current user's role.
    ---
    tags:
      - RBAC
    security:
      - BearerAuth: []
    responses:
      200:
        description: Role permissions returned
      401:
        description: Invalid or missing JWT
    """
    return permissions()


@rbac_bp.route("/check", methods=["POST"])
@jwt_required
def check_route():
    """
    Check whether the current role can access an endpoint/method.
    ---
    tags:
      - RBAC
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - endpoint
            - method
          properties:
            endpoint:
              type: string
            method:
              type: string
    responses:
      200:
        description: Access check result returned
      401:
        description: Invalid or missing JWT
    """
    return check()


@rbac_bp.route("/users", methods=["GET"])
@jwt_required
@role_required("teacher")
def users_route():
    """
    List users with optional role filter.
    ---
    tags:
      - RBAC
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: role
        type: string
        required: false
    responses:
      200:
        description: User list returned
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return users()


@rbac_bp.route("/users/<user_id>/toggle", methods=["PATCH"])
@jwt_required
@role_required("teacher")
def toggle_route(user_id):
    """
    Toggle a user's active status.
    ---
    tags:
      - RBAC
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
    responses:
      200:
        description: User status toggled
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
      404:
        description: User not found
    """
    return toggle(user_id)


@rbac_bp.route("/health", methods=["GET"])
def health_route():
    """
    RBAC module health check.
    ---
    tags:
      - RBAC
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
