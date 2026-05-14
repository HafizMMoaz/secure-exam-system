"""
EXAMPLE - How to use responses and exceptions in any module route.
This file is NOT part of the actual system. Delete when done reading.
"""

from flask import Blueprint, request
from middleware.jwt_auth import jwt_required, role_required
from responses import success_response, error_response, health_response
from exceptions import (
    BadRequestException,
    NotFoundException,
    ExamStateException,
    DatabaseException,
)

example_bp = Blueprint("example", __name__)


# ── Success response ───────────────────────────────────────────────────────────
@example_bp.route("/api/example/data", methods=["GET"])
@jwt_required
def get_data():
    data = {"items": [1, 2, 3]}
    return success_response(data=data, message="Data fetched successfully")
    # -> { "status": "success", "data": {"items": [1,2,3]}, "message": "..." }


# ── Raising a custom exception ─────────────────────────────────────────────────
@example_bp.route("/api/example/item/<item_id>", methods=["GET"])
@jwt_required
def get_item(item_id):
    item = None  # pretend DB lookup failed
    if not item:
        raise NotFoundException(f"Item '{item_id}' not found")
        # -> { "status": "error", "error_code": 404, "message": "...", "timestamp": "..." }

    return success_response(data=item)


# ── Validating request body ────────────────────────────────────────────────────
@example_bp.route("/api/example/submit", methods=["POST"])
@jwt_required
def submit():
    body = request.get_json()
    if not body or "exam_id" not in body:
        raise BadRequestException("exam_id is required")

    return success_response(message="Submitted successfully")


# ── Exam state machine check ───────────────────────────────────────────────────
@example_bp.route("/api/example/exam-action", methods=["POST"])
@jwt_required
def exam_action():
    current_state = "SUBMITTED"   # fetched from DB
    required_state = "IN_PROGRESS"

    if current_state != required_state:
        raise ExamStateException(
            current_state=current_state,
            required_state=required_state
        )
        # -> HTTP 409 { "status": "error", "error_code": 409, "message": "Exam is in state 'SUBMITTED', expected 'IN_PROGRESS'" }

    return success_response(message="Action performed")


# ── Teacher-only route ─────────────────────────────────────────────────────────
@example_bp.route("/api/example/teacher-only", methods=["GET"])
@jwt_required
@role_required("teacher")
def teacher_route():
    return success_response(data={"secret": "teacher stuff"})


# ── Health check (every module needs this) ────────────────────────────────────
@example_bp.route("/api/example/health", methods=["GET"])
def health():
    return health_response(
        module_name="Module_X_Example",
        dependencies=["mongodb"],
        version="1.0.0",
        healthy=True
    )
    # -> { "module": "Module_X_Example", "status": "healthy", "dependencies": [...], "version": "1.0.0" }