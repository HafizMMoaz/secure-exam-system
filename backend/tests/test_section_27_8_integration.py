"""
PRD §27.8 integration test suite — the four MUST-pass tests.

1. JWT test:    Call API with expired JWT → HTTP 401
2. Logging:     Generate a log via gateway → verify it appears in logs collection
3. Health:      GET /api/<mod>/health returns 200 in under 1 second (all 17 modules)
4. State:       Attempt an exam action in the wrong state → HTTP 409
"""

import time
from datetime import datetime, timezone

import pytest
import requests


# 1. JWT expiry test (§27.8.1)
EXPIRED_JWT_PROBES = [
    "/api/auth/profile",
    "/api/questions/exams/list",
    "/api/risk/dashboard/000000000000000000000000",
    "/api/rbac/users",
]


@pytest.mark.parametrize("path", EXPIRED_JWT_PROBES)
def test_expired_jwt_returns_401(base_url, expired_teacher_token, path):
    r = requests.get(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {expired_teacher_token}"},
        timeout=5,
    )
    assert r.status_code == 401, f"{path} returned {r.status_code}, expected 401"


# 2. Logging gateway round-trip (§27.8.2)
def test_log_gateway_round_trip(base_url, db, teacher_token):
    token, user_id = teacher_token
    action = f"pytest_action_{int(time.time() * 1000)}"

    payload = {
        "module": "Module_1_Auth",  # any valid ModuleName enum value
        "level": "INFO",
        "user_id": user_id,
        "exam_id": "test_exam",
        "action": action,
        "details": {"note": "round-trip test"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    r = requests.post(
        f"{base_url}/api/logs/write",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert r.status_code in (200, 202), f"log gateway returned {r.status_code}: {r.text[:200]}"

    deadline = time.monotonic() + 2.0
    doc = None
    while time.monotonic() < deadline:
        doc = db.logs.find_one({"action": action})
        if doc:
            break
        time.sleep(0.1)
    assert doc is not None, "log document never appeared in logs collection"
    assert doc.get("integrity_hash"), "log document missing integrity_hash"


# 3. Per-module health latency (§27.8.3)
MODULE_HEALTH_PATHS = [
    "/api/auth/health",
    "/api/session/health",
    "/api/device/health",
    "/api/activation/health",
    "/api/rbac/health",
    "/api/questions/health",
    "/api/randomization/health",
    "/api/timer/health",
    "/api/validation/health",
    "/api/tab/health",
    "/api/clipboard/health",
    "/api/activity/health",
    "/api/logs/health",
    "/api/multisession/health",
    "/api/behavioral/health",
    "/api/similarity/health",
    "/api/risk/health",
]


@pytest.mark.parametrize("path", MODULE_HEALTH_PATHS)
def test_module_health_under_1s(base_url, path):
    start = time.monotonic()
    r = requests.get(f"{base_url}{path}", timeout=5)
    elapsed = time.monotonic() - start
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    assert elapsed < 1.0, f"{path} took {elapsed:.3f}s, must be < 1.0s"


# 4. Wrong-state exam action (§27.8.4)
def test_answer_submit_in_wrong_state_returns_409(base_url, seeded_exam, student_token):
    """
    Seeded exam is in NOT_STARTED. Submitting an answer requires IN_PROGRESS,
    so the server must return 409 Conflict per §27.2.
    """
    token, _ = student_token
    payload = {
        "exam_id": seeded_exam["exam_id"],
        "question_id": seeded_exam["question_id"],
        "answer": "premature",
        "time_taken_seconds": 5.0,
    }
    r = requests.post(
        f"{base_url}/api/questions/answer/save",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text[:200]}"


def test_risk_compute_in_wrong_state_returns_409(base_url, seeded_exam, teacher_token):
    """
    Risk compute requires SUBMITTED or ANALYZING. Seeded exam is NOT_STARTED.
    """
    token, _ = teacher_token
    r = requests.post(
        f"{base_url}/api/risk/compute/{seeded_exam['exam_id']}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text[:200]}"
