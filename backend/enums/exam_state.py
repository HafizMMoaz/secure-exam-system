from enum import Enum


class ExamState(str, Enum):
    """
    Exam state machine - section 27.4 of the spec.
    Order matters: transitions must follow this sequence.

    NOT_STARTED -> DEVICE_VERIFIED -> TEACHER_APPROVED
    -> ACTIVATION_VALID -> IN_PROGRESS -> SUBMITTED
    -> ANALYZING -> COMPLETED
    """
    NOT_STARTED      = "NOT_STARTED"
    DEVICE_VERIFIED  = "DEVICE_VERIFIED"
    TEACHER_APPROVED = "TEACHER_APPROVED"
    ACTIVATION_VALID = "ACTIVATION_VALID"
    IN_PROGRESS      = "IN_PROGRESS"
    SUBMITTED        = "SUBMITTED"
    ANALYZING        = "ANALYZING"
    COMPLETED        = "COMPLETED"

    # Ordered list for transition validation
    _order = None  # populated below

    @classmethod
    def order(cls):
        return [
            cls.NOT_STARTED,
            cls.DEVICE_VERIFIED,
            cls.TEACHER_APPROVED,
            cls.ACTIVATION_VALID,
            cls.IN_PROGRESS,
            cls.SUBMITTED,
            cls.ANALYZING,
            cls.COMPLETED,
        ]

    def can_transition_to(self, next_state: "ExamState") -> bool:
        """Check if transitioning to next_state is valid (must be the immediate next step)."""
        order = ExamState.order()
        try:
            return order.index(next_state) == order.index(self) + 1
        except ValueError:
            return False

    @classmethod
    def monitoring_active_states(cls):
        """States where Modules 10-13 (monitoring) are active."""
        return [cls.IN_PROGRESS]

    @classmethod
    def submission_allowed_states(cls):
        """States where answer submission is allowed."""
        return [cls.IN_PROGRESS]

    @classmethod
    def risk_scoring_states(cls):
        """States where Module 17 (risk scoring) runs."""
        return [cls.ANALYZING]