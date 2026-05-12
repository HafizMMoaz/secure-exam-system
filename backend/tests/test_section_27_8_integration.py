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


# 5. OTP MFA flow (Phase 5.3)
def test_otp_mfa_round_trip(base_url, db):
    """
    Register a user, request OTP (Step 1), pick the code out of the
    logs collection (dev delivery channel), verify OTP (Step 2), and
    confirm the returned JWT unlocks /api/auth/profile.
    """
    import bcrypt
    from bson import ObjectId

    user_id = ObjectId()
    db.users.insert_one({
        "_id": user_id,
        "username": "otp_user",
        "password_hash": bcrypt.hashpw(b"correcthorse", bcrypt.gensalt()).decode(),
        "role": "teacher",
        "is_active": True,
    })

    r = requests.post(
        f"{base_url}/api/auth/otp/request",
        json={"username": "otp_user", "password": "correcthorse"},
        timeout=5,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["otp_sent"] is True

    deadline = time.monotonic() + 2.0
    log_doc = None
    while time.monotonic() < deadline:
        log_doc = db.logs.find_one({"action": "otp_issued", "user_id": str(user_id)})
        if log_doc:
            break
        time.sleep(0.1)
    assert log_doc is not None, "otp_issued log never appeared"
    code = log_doc.get("details", {}).get("code")
    assert code and len(code) == 6, f"OTP code not in log details: {log_doc}"

    r = requests.post(
        f"{base_url}/api/auth/otp/verify",
        json={"username": "otp_user", "code": code},
        timeout=5,
    )
    assert r.status_code == 200, r.text
    token = r.json()["data"]["token"]
    assert token

    r = requests.get(
        f"{base_url}/api/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert r.status_code == 200, r.text


def test_otp_wrong_code_rejected(base_url, db):
    import bcrypt
    from bson import ObjectId

    user_id = ObjectId()
    db.users.insert_one({
        "_id": user_id,
        "username": "otp_bad",
        "password_hash": bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
        "role": "teacher",
        "is_active": True,
    })

    requests.post(
        f"{base_url}/api/auth/otp/request",
        json={"username": "otp_bad", "password": "x"},
        timeout=5,
    )

    r = requests.post(
        f"{base_url}/api/auth/otp/verify",
        json={"username": "otp_bad", "code": "000000"},
        timeout=5,
    )
    assert r.status_code == 401, r.text


# 9. SSE live-monitoring stream (Phase 4 / §24 bonus)
def test_sse_stream_emits_stream_open_event(base_url, db, teacher_token, seeded_exam):
    """
    The SSE endpoint must immediately emit a `stream_open` event when a
    teacher connects. We accept the JWT via ?token= because EventSource
    cannot set custom headers.
    """
    token, _ = teacher_token
    url = f"{base_url}/api/risk/stream/{seeded_exam['exam_id']}?token={token}"
    with requests.get(url, stream=True, timeout=5) as r:
        assert r.status_code == 200
        assert r.headers.get("Content-Type", "").startswith("text/event-stream")
        # Read just enough to see the first event.
        chunks = []
        for line in r.iter_lines(decode_unicode=True):
            chunks.append(line)
            if line.startswith("data:"):
                break
            if len(chunks) > 6:
                break
        joined = "\n".join(chunks)
        assert "stream_open" in joined, f"no stream_open event: {joined!r}"


# 8. Module 9 input validation integration (Phase 5.5)
def test_nosql_injection_in_login_returns_400(base_url):
    """
    Login body containing a Mongo operator string must be rejected by
    the @validate_body wrapper. Without Module 9, this string would be
    passed verbatim into a pymongo find_one.
    """
    r = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": {"$ne": None}, "password": "x"},
        timeout=5,
    )
    # The validator rejects nested operators as a NoSQL-style payload.
    assert r.status_code == 400, f"got {r.status_code}: {r.text[:200]}"


def test_xss_in_register_username_returns_400(base_url):
    r = requests.post(
        f"{base_url}/api/auth/register",
        json={"username": "<script>alert(1)</script>", "password": "x", "role": "student"},
        timeout=5,
    )
    assert r.status_code == 400, f"got {r.status_code}: {r.text[:200]}"


# 7. Rate limiting on auth (Phase 5.4)
def test_login_rate_limit_kicks_in(base_url):
    """
    /api/auth/login is limited to 5 per minute per IP. The 6th request
    within a minute must return 429.
    """
    seen_429 = False
    for _ in range(8):
        r = requests.post(
            f"{base_url}/api/auth/login",
            json={"username": "no_such_user", "password": "x"},
            timeout=5,
        )
        if r.status_code == 429:
            seen_429 = True
            break
    assert seen_429, "expected 429 within 8 rapid login attempts"


# 6. Log integrity verification (Phase 5.1)
def test_log_integrity_verify_detects_tamper(base_url, db, teacher_token):
    """
    Write a log via the gateway, hand-edit the stored document in Mongo,
    then call /api/logs/verify and assert the entry surfaces as tampered.
    Demonstrates the §27.3 SHA-256 integrity claim.
    """
    token, user_id = teacher_token
    action = f"pytest_tamper_{int(time.time() * 1000)}"

    payload = {
        "module": "Module_1_Auth",
        "level": "INFO",
        "user_id": user_id,
        "exam_id": "test_exam",
        "action": action,
        "details": {"note": "original"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r = requests.post(
        f"{base_url}/api/logs/write",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert r.status_code in (200, 202)

    # Tamper directly in Mongo without recomputing the hash.
    result = db.logs.update_one(
        {"action": action},
        {"$set": {"details": {"note": "TAMPERED"}}},
    )
    assert result.modified_count == 1

    r = requests.get(
        f"{base_url}/api/logs/verify?action={action}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 200, r.text[:200]
    data = r.json().get("data", {})
    tampered_actions = [t.get("action") for t in data.get("tampered", [])]
    assert action in tampered_actions, (
        f"tampered entry not detected. data={data}"
    )
    assert data.get("all_intact") is False
