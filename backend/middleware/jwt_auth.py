"""
JWT Authentication Middleware.

Decorators:
    @jwt_required           - validates JWT, attaches payload to request.user
    @role_required("teacher") - enforces RBAC on top of JWT validation

Usage:
    from middleware.jwt_auth import jwt_required, role_required

    @bp.route("/api/auth/profile")
    @jwt_required
    def profile():
        user = request.user  # { user_id, username, role, session_id, ... }
        ...

    @bp.route("/api/questions/create")
    @jwt_required
    @role_required("teacher")
    def create_question():
        ...
"""

import jwt
from functools import wraps
from flask import request

from config.config import JWT_SECRET
from exceptions import (
    JWTMissingException,
    JWTExpiredException,
    JWTInvalidException,
    ForbiddenException,
)


def jwt_required(f):
    """
    Validates JWT from Authorization: Bearer <token> header.
    Attaches decoded payload to request.user on success.
    Raises 401 on any failure.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        elif request.args.get("token"):
            # EventSource cannot set custom headers - accept JWT via ?token=
            # query parameter for SSE endpoints. Only enabled because the
            # endpoints that use SSE are read-only and idempotent.
            token = request.args.get("token")
        else:
            raise JWTMissingException()

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            request.user = payload
        except jwt.ExpiredSignatureError:
            raise JWTExpiredException()
        except jwt.InvalidTokenError:
            raise JWTInvalidException()

        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """
    Enforces role-based access control.
    Must be used AFTER @jwt_required - relies on request.user being set.
    Raises 403 if user's role is not in the allowed roles list.

    Example:
        @jwt_required
        @role_required("teacher")
        def teacher_only_route(): ...

        @jwt_required
        @role_required("student", "teacher")
        def shared_route(): ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(request, "user", None)
            if not user or user.get("role") not in roles:
                raise ForbiddenException(
                    f"Role '{user.get('role') if user else 'unknown'}' "
                    f"is not allowed. Required: {list(roles)}"
                )
            return f(*args, **kwargs)
        return decorated
    return decorator