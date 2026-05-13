# Security Overview

This document summarizes the security architecture, integration contract, and practical guidance for modules in the Secure Online Examination System.

## Threat Model (high level)

- Cheating via tab switching, answer copying, multiple sessions, credential sharing.
- Injection or malformed inputs targeting backend APIs.
- Replay of authentication tokens or stolen tokens.
- Tampering with logs or audit trails.

## Authentication & JWT (Module 1)

- Only Module 1 issues JWTs.
- Token format: header.payload.signature (signed JWT).
- Algorithm: HS256 (HMAC-SHA256) by default.
- Required JWT payload claims:
  - `user_id` (string)
  - `username` (string)
  - `role` ("student" | "teacher")
  - `session_id` (string)
  - `device_fingerprint_hash` (string)
  - `exp` (numeric timestamp)

Example payload (conceptual):

```json
{
  "user_id": "...",
  "username": "student01",
  "role": "student",
  "session_id": "...",
  "device_fingerprint_hash": "...",
  "exp": 1712345678
}
```

Validation rules (must be enforced by every module except login/register):
1. Extract token from header: `Authorization: Bearer <token>`
2. Verify signature with the shared secret (instructor-provided)
3. Check `exp` has not passed
4. Reject with 401 on any failure

Notes:
- If you change to asymmetric signing (e.g. RS256), update both issuer and verifier.
- Keep secrets out of source — load via environment variables or secure vaults.

## Passwords

- Always store password hashes using `bcrypt`.
- Use per-password salts (bcrypt provides this) and an appropriate work factor.

## Session Management

- JWT contains `session_id` to detect session reuse/duplicate sessions.
- Sessions should be short-lived; use refresh strategies if needed.

## Role-Based Access Control (RBAC)

- Role carried inside JWT (`role`) and enforced by each module.
- Return 403 when role is insufficient.

## Device Fingerprinting & Multi-Session Detection

- Device fingerprint stored in `device_fingerprint_hash` claim.
- Module 3 and Module 14 should compare fingerprints and detect account sharing.

## Logging & Log Integrity

- All modules MUST send logs to the central logging endpoint `POST /api/logs/write`.
- No module writes directly to `logs` collection.
- Log entries must contain: `module`, `level`, `user_id`, `exam_id`, `action`, `details`, `timestamp`.
- Log integrity: optionally compute SHA-256 chain or HMAC over log batches to detect tampering.

## Exam State Machine

All exam-related actions must respect the canonical state machine:

```
NOT_STARTED -> DEVICE_VERIFIED -> TEACHER_APPROVED -> ACTIVATION_VALID -> IN_PROGRESS -> SUBMITTED -> ANALYZING -> COMPLETED
```

Enforce allowed transitions and return 409 for invalid state actions.

## API Security Best Practices

- Require `Authorization: Bearer <token>` for protected endpoints.
- Validate all input (server-side) and sanitize before DB operations.
- Use parameterized queries for DB access (Mongo driver best practices).
- Rate-limit sensitive endpoints (login, activation).
- Use HTTPS in production; do not serve tokens over plain HTTP.
- Enable CORS policy narrowly (whitelist frontend origins).

## Secrets & Key Management

- Store `JWT_SECRET` and DB credentials in environment variables or a secrets manager.
- Rotate secrets periodically and provide backward-compatible key acceptance during rotation if needed.

## Deployment Recommendations

- Run backend behind an HTTPS reverse proxy (Nginx, cloud load balancer).
- Ensure MongoDB is secured (auth enabled, bind to internal network).
- Limit logging data to required fields and avoid logging secrets.

## Testing & Integration Checklist

- JWT test: expired, invalid, missing token → 401 responses.
- RBAC test: valid token but insufficient role → 403.
- Logging test: create log from module → ensure it appears via logging gateway.
- Health test: `GET /api/health` → 200 in <1s.
- State test: illegal state transition → 409.

## Contact / Incident

- If you find a security issue, report to the instructor or repository owner immediately and do not publish details publicly.

---

This file is a concise developer-facing reference — link to it from the main README and refer to module specifications for per-module security details.


For any issue or bug report contact hafizmoazkhalid@gmail.com
