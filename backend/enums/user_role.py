from enum import Enum


class UserRole(str, Enum):
    """
    User roles - from JWT payload spec section 27.1.
    role: "student | teacher"
    """
    STUDENT = "student"
    TEACHER = "teacher"