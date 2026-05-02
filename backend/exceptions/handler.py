"""
Global exception handler.
Register this with the Flask app so all custom exceptions
are automatically caught and returned as proper JSON responses.

Usage in app.py:
    from exceptions.handler import register_error_handlers
    register_error_handlers(app)
"""

from flask import jsonify
from datetime import datetime, timezone
from .exceptions import SecureExamBaseException


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def register_error_handlers(app):
    """Attach all error handlers to the Flask app."""

    # ── Custom exceptions ──────────────────────────────────────────────────────
    @app.errorhandler(SecureExamBaseException)
    def handle_custom_exception(e):
        return jsonify(e.to_dict()), e.status_code

    # ── Flask built-in HTTP errors ─────────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "status": "error",
            "error_code": 400,
            "message": "Bad request",
            "timestamp": _timestamp()
        }), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({
            "status": "error",
            "error_code": 401,
            "message": "Unauthorized",
            "timestamp": _timestamp()
        }), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({
            "status": "error",
            "error_code": 403,
            "message": "Forbidden",
            "timestamp": _timestamp()
        }), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "status": "error",
            "error_code": 404,
            "message": "Resource not found",
            "timestamp": _timestamp()
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            "status": "error",
            "error_code": 405,
            "message": "Method not allowed",
            "timestamp": _timestamp()
        }), 405

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({
            "status": "error",
            "error_code": 409,
            "message": "Conflict",
            "timestamp": _timestamp()
        }), 409

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            "status": "error",
            "error_code": 500,
            "message": "Internal server error",
            "timestamp": _timestamp()
        }), 500

    @app.errorhandler(503)
    def service_unavailable(e):
        return jsonify({
            "status": "error",
            "error_code": 503,
            "message": "Service unavailable",
            "timestamp": _timestamp()
        }), 503