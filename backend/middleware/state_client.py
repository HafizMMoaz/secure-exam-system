"""
Shared client for the central exam-state-transition endpoint
(PUT /api/auth/exam/state/<exam_id>).

Per PRD §27.6 (strict), Module 1 is the sole writer of exams_col.state.
Other modules call this helper instead of writing the collection
directly. The helper forwards the caller's JWT so the §27.4 transition
validation runs against the same authenticated request.
"""

import requests

from config.config import BASE_URL
from exceptions import DatabaseException, ExamStateException


def transition_exam_state(exam_id, target_state, auth_header, actor_module):
    """
    POST a state transition request to Module 1. Returns the auth
    endpoint's response payload on success; raises on failure.

    Raises ExamStateException if Module 1 returns 409 (transition not
    allowed from current state) so the caller can propagate the same
    §27.2 error response shape it would have raised locally.
    """
    if not exam_id:
        raise DatabaseException("exam_id required for state transition")

    url = f"{BASE_URL}/api/auth/exam/state/{exam_id}"
    headers = {"Authorization": auth_header} if auth_header else {}
    body = {"to": target_state, "actor_module": actor_module}

    try:
        response = requests.put(url, json=body, headers=headers, timeout=5)
    except requests.RequestException as exc:
        raise DatabaseException(f"State endpoint unreachable: {exc}")

    if response.status_code == 200:
        return response.json().get("data", {})

    if response.status_code == 409:
        try:
            current = response.json().get("data", {}).get("current_state", "unknown")
        except Exception:
            current = "unknown"
        raise ExamStateException(current_state=current, required_state=target_state)

    raise DatabaseException(
        f"State endpoint returned {response.status_code}: {response.text[:200]}"
    )
