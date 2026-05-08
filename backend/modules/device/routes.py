from flask import Blueprint

from middleware.jwt_auth import jwt_required
from modules.device.controller import register, verify, list_all, health

device_bp = Blueprint("device_bp", __name__)


@device_bp.route("/register", methods=["POST"])
@jwt_required
def register_route():
    """
    Register a device fingerprint for the authenticated user.
    ---
    tags:
      - Device
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_agent
            - screen_resolution
            - timezone
            - language
            - platform
          properties:
            user_agent:
              type: string
            screen_resolution:
              type: string
            timezone:
              type: string
            language:
              type: string
            platform:
              type: string
    responses:
      200:
        description: Device registered or already registered
      401:
        description: Invalid or missing JWT
    """
    return register()


@device_bp.route("/verify", methods=["POST"])
@jwt_required
def verify_route():
    """
    Verify whether current device matches a trusted fingerprint.
    ---
    tags:
      - Device
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_agent
            - screen_resolution
            - timezone
            - language
            - platform
          properties:
            user_agent:
              type: string
            screen_resolution:
              type: string
            timezone:
              type: string
            language:
              type: string
            platform:
              type: string
    responses:
      200:
        description: Device trust status returned
      401:
        description: Invalid or missing JWT
    """
    return verify()


@device_bp.route("/list", methods=["GET"])
@jwt_required
def list_route():
    """
    List all registered devices for the authenticated user.
    ---
    tags:
      - Device
    security:
      - BearerAuth: []
    responses:
      200:
        description: Device list returned
      401:
        description: Invalid or missing JWT
    """
    return list_all()


@device_bp.route("/health", methods=["GET"])
def health_route():
    """
    Device module health check.
    ---
    tags:
      - Device
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
