"""
Custom exceptions for the Secure Exam System.
Each exception maps to a specific HTTP status code defined in section 27.2.

Usage:
    raise BadRequestException("exam_id is required")
    raise UnauthorizedException("JWT expired")
    raise ForbiddenException("Students cannot access this endpoint")
    raise NotFoundException("Exam not found")
    raise ConflictException("Exam already submitted")
    raise InternalException("Database connection failed")
    raise ServiceUnavailableException("Module_13_Logging is down")
    raise ExamStateException("Action not allowed in current exam state")
"""


class SecureExamBaseException(Exception):
    """Base exception — all custom exceptions inherit from this."""
    status_code = 500
    default_message = "An unexpected error occurred"

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)

    def to_dict(self):
        from datetime import datetime, timezone
        return {
            "status": "error",
            "error_code": self.status_code,
            "message": self.message,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }


# ── 400 Bad Request ────────────────────────────────────────────────────────────
class BadRequestException(SecureExamBaseException):
    """Missing or invalid request parameters."""
    status_code = 400
    default_message = "Bad request — missing or invalid parameters"


# ── 401 Unauthorized ───────────────────────────────────────────────────────────
class UnauthorizedException(SecureExamBaseException):
    """Invalid or missing JWT token."""
    status_code = 401
    default_message = "Unauthorized — invalid or missing JWT"


class JWTExpiredException(UnauthorizedException):
    """JWT token has expired."""
    default_message = "JWT expired"


class JWTInvalidException(UnauthorizedException):
    """JWT token signature or format is invalid."""
    default_message = "Invalid JWT"


class JWTMissingException(UnauthorizedException):
    """No JWT token provided in request."""
    default_message = "Missing Authorization header"


# ── 403 Forbidden ──────────────────────────────────────────────────────────────
class ForbiddenException(SecureExamBaseException):
    """Valid JWT but insufficient role permissions (RBAC violation)."""
    status_code = 403
    default_message = "Forbidden — insufficient permissions"


# ── 404 Not Found ─────────────────────────────────────────────────────────────
class NotFoundException(SecureExamBaseException):
    """Requested resource does not exist."""
    status_code = 404
    default_message = "Resource not found"


class UserNotFoundException(NotFoundException):
    default_message = "User not found"


class ExamNotFoundException(NotFoundException):
    default_message = "Exam not found"


class QuestionNotFoundException(NotFoundException):
    default_message = "Question not found"


class DeviceNotFoundException(NotFoundException):
    default_message = "Device not found"


class SessionNotFoundException(NotFoundException):
    default_message = "Session not found"


# ── 409 Conflict ──────────────────────────────────────────────────────────────
class ConflictException(SecureExamBaseException):
    """State violation — e.g. exam already submitted."""
    status_code = 409
    default_message = "Conflict — state violation"


class ExamAlreadySubmittedException(ConflictException):
    default_message = "Exam already submitted"


class UserAlreadyExistsException(ConflictException):
    default_message = "User already exists"


class SessionAlreadyActiveException(ConflictException):
    default_message = "Another session is already active for this user"


class ActivationCodeAlreadyUsedException(ConflictException):
    default_message = "Activation code has already been used"


# ── 409 Exam State Machine Violation ──────────────────────────────────────────
class ExamStateException(ConflictException):
    """
    Action attempted in wrong exam state.
    e.g. submitting answers when state is not IN_PROGRESS.
    
    Valid states: NOT_STARTED → DEVICE_VERIFIED → TEACHER_APPROVED
                  → ACTIVATION_VALID → IN_PROGRESS → SUBMITTED
                  → ANALYZING → COMPLETED
    """
    default_message = "Action not allowed in current exam state"

    def __init__(self, message=None, current_state=None, required_state=None):
        if not message and current_state and required_state:
            message = f"Exam is in state '{current_state}', expected '{required_state}'"
        super().__init__(message)


# ── 500 Internal Server Error ─────────────────────────────────────────────────
class InternalException(SecureExamBaseException):
    """Module crashed or dependency failed."""
    status_code = 500
    default_message = "Internal server error"


class DatabaseException(InternalException):
    default_message = "Database operation failed"


# ── 503 Service Unavailable ───────────────────────────────────────────────────
class ServiceUnavailableException(SecureExamBaseException):
    """A dependent module is down."""
    status_code = 503
    default_message = "Dependent service is unavailable"

    def __init__(self, message=None, dependent_module=None):
        if not message and dependent_module:
            message = f"Dependent module '{dependent_module}' is unavailable"
        super().__init__(message)