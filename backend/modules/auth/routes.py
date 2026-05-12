from flask import Blueprint

from modules.auth.controller import (
    exam_state,
    health,
    login,
    otp_request_action,
    otp_verify_action,
    profile,
    register,
)
from middleware.jwt_auth import jwt_required
from middleware.rate_limit import (
    limiter,
    AUTH_LOGIN_LIMIT,
    AUTH_OTP_REQUEST_LIMIT,
    AUTH_OTP_VERIFY_LIMIT,
)
from middleware.validate_body import validate_body


auth_bp = Blueprint("auth_bp", __name__)


@auth_bp.route("/register", methods=["POST"])
@validate_body
def register_route():
    """
    Register a new user.
    ---
    tags:
      - Auth
    security: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
            - role
          properties:
            username:
              type: string
              example: student01
            password:
              type: string
              example: strong-password
            role:
              type: string
              enum:
                - student
                - teacher
              example: student
    responses:
      200:
        description: User registered successfully
        schema:
          $ref: '#/definitions/SuccessResponse'
      400:
        description: Missing or invalid parameters
    """
    return register()


@auth_bp.route("/login", methods=["POST"])
@limiter.limit(AUTH_LOGIN_LIMIT)
@validate_body
def login_route():
    """
    Authenticate a user and return a JWT.
    ---
    tags:
      - Auth
    security: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: student01
            password:
              type: string
              example: strong-password
    responses:
      200:
        description: Login successful
        schema:
          $ref: '#/definitions/SuccessResponse'
      400:
        description: Missing or invalid parameters
      401:
        description: Invalid credentials or JWT issue
    """
    return login()


@auth_bp.route("/otp/request", methods=["POST"])
@limiter.limit(AUTH_OTP_REQUEST_LIMIT)
@validate_body
def otp_request_route():
    """
    Step 1 of MFA — verify password and issue a one-time code. The code
    is delivered through the §27.3 logging gateway in dev mode.
    ---
    tags:
      - Auth
    security: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
            password:
              type: string
    responses:
      200:
        description: OTP issued
      401:
        description: Invalid credentials
    """
    return otp_request_action()


@auth_bp.route("/otp/verify", methods=["POST"])
@limiter.limit(AUTH_OTP_VERIFY_LIMIT)
@validate_body
def otp_verify_route():
    """
    Step 2 of MFA — submit the OTP and receive a JWT.
    ---
    tags:
      - Auth
    security: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - code
          properties:
            username:
              type: string
            code:
              type: string
    responses:
      200:
        description: JWT issued
      401:
        description: Invalid or expired OTP
    """
    return otp_verify_action()


@auth_bp.route("/profile", methods=["GET"])
@jwt_required
def profile_route():
    """
    Return the authenticated user's profile.
    ---
    tags:
      - Auth
    security:
      - BearerAuth: []
    responses:
      200:
        description: Profile returned successfully
        schema:
          $ref: '#/definitions/SuccessResponse'
      401:
        description: Invalid or missing JWT
      404:
        description: User not found
    """
    return profile()


@auth_bp.route("/exam/state/<exam_id>", methods=["GET"])
@jwt_required
def exam_state_route(exam_id):
    """
    Return the current exam state.
    ---
    tags:
      - Auth
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
        description: Exam identifier
    responses:
      200:
        description: Exam state returned successfully
        schema:
          $ref: '#/definitions/SuccessResponse'
      401:
        description: Invalid or missing JWT
      404:
        description: Exam not found
    """
    return exam_state(exam_id)


@auth_bp.route("/health", methods=["GET"])
def health_route():
    """
    Module health check.
    ---
    tags:
      - Auth
    security: []
    responses:
      200:
        description: Module health returned successfully
        schema:
          $ref: '#/definitions/HealthResponse'
    """
    return health()