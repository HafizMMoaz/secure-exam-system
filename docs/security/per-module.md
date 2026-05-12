# Per-Module Security Brief

The PRD §6 requires every module to answer three questions:

> 1. What security problem is solved?
> 2. What attack is prevented?
> 3. How is it implemented?

This document is the consolidated answer for all 17 modules, plus the
cross-cutting integrity guarantees from PRD §27. It is the canonical
source for the **Concept Understanding** rubric line (§25, 10 marks).

See `ARCHITECTURE.md` for the data ownership model that backs these
mechanisms.

---

## Module 1 — Secure Authentication

**Problem.** Bare username/password storage and naive login expose the
system to credential theft via DB dumps and replay of intercepted
credentials.

**Attack prevented.** Offline brute-force / rainbow-table recovery of
plaintext passwords; replay of stolen passwords once an account is
compromised by adding a second factor.

**How.**
- bcrypt with per-user salt for `password_hash` (`auth/service.py`).
  bcrypt's adaptive cost makes offline cracking expensive even with a
  full DB dump.
- HS256 JWT issued on login; payload follows PRD §27.1 — `user_id`,
  `username`, `role`, `session_id`, `device_fingerprint_hash`, `exp`.
- OTP-based MFA on top of password verification (Phase 5.3, `auth/service.py`
  `request_otp`/`verify_otp`). Six-digit code, single-use, 5-minute TTL,
  delivered through the §27.3 logging gateway in dev mode.

---

## Module 2 — Secure Session Management

**Problem.** A long-lived bearer token re-used after sign-out, theft,
or revocation lets an attacker impersonate the user indefinitely.

**Attack prevented.** Session fixation, stolen-token replay past the
intended session boundary, and lingering sessions after logout.

**How.**
- Every JWT carries a `session_id`. Module 2 maintains a `sessions`
  collection keyed by `session_id` with `is_active`, `expires_at`,
  `last_activity`.
- The JWT middleware validates the `session_id` is active before
  honoring the token, so logout (deactivate the session) immediately
  invalidates all tokens bound to it.
- Hard expiry via the JWT `exp` claim (default 60 min, configurable
  via `JWT_EXPIRY_MINUTES`).

---

## Module 3 — Device Fingerprinting

**Problem.** A student logs in, then shares the password with someone
else who logs in from a different device — credential sharing.

**Attack prevented.** Account sharing during an exam; concurrent use
of one account from multiple devices.

**How.**
- Browser-side fingerprint hash is computed in `useDeviceFingerprint.ts`
  (UA, screen size, language, time-zone, hardware concurrency, canvas
  hash) and registered with `POST /api/device/register`.
- The fingerprint is stored on the user document and bound into the
  JWT as `device_fingerprint_hash`. Every request the auth middleware
  checks the JWT's claim against the registered device.

---

## Module 4 — Activation Code Security

**Problem.** Anyone who knows an exam ID could start the exam at any
time, breaking exam-window guarantees.

**Attack prevented.** Out-of-window exam access; activation-code reuse
across attempts.

**How.**
- One-time activation codes are minted per exam by the teacher and
  bound to a validity window. `POST /api/activation/generate` and
  `POST /api/activation/validate` (`activation/service.py`).
- Successful validation transitions the exam state to
  `ACTIVATION_VALID` (§27.4) — every downstream module gates on this
  state, so a missing activation step locks the rest of the flow.

---

## Module 5 — RBAC

**Problem.** Without role-based gating, any authenticated user could
hit any endpoint — students could view risk dashboards, etc.

**Attack prevented.** Horizontal and vertical privilege escalation by
authenticated users.

**How.**
- `@role_required("teacher" | "student")` decorator in
  `middleware/jwt_auth.py`, applied to every endpoint that has a role
  scope.
- Role is taken from the JWT claim (signed by Module 1), so clients
  cannot lie about their role.
- Module 5 also owns `is_active` mutations — an admin can deactivate
  a student mid-exam and revoke access immediately (see
  `ARCHITECTURE.md` for why §27.6 is refined this way).

---

## Module 6 — Secure Question Delivery

**Problem.** Question text leaking before the exam window opens, or
being reachable by unenrolled students, defeats the assessment.

**Attack prevented.** Pre-exam question disclosure; cross-enrollment
question access.

**How.**
- Every read endpoint (`get_all_questions_for_student`, etc.) checks
  exam state (`IN_PROGRESS` for delivery to students, see §27.4) and
  student enrollment+approval.
- Teacher CRUD endpoints check teacher ownership of the exam.
- Answer writes go to `responses_col.answer_text`, which the integrity
  module (Similarity) reads for collusion checks.

---

## Module 7 — Question Randomization

**Problem.** A fixed question order lets two students sitting near
each other copy answers position-by-position.

**Attack prevented.** Position-based collusion; pre-arranged answer
sharing by index.

**How.**
- Deterministic seeded shuffle: seed = `hash(exam_id || student_id)`,
  so each student gets a stable random order across reloads, and no
  two students see the same order. `randomization/service.py`.
- Stored in `randomized_orders_col` to ensure consistency between
  delivery and grading.

---

## Module 8 — Secure Timer

**Problem.** A client-side timer is trivially bypassed: the student
just edits the DOM or `localStorage` to extend the deadline.

**Attack prevented.** Time extension; submission after the window
closes.

**How.**
- Timer state lives in `exam_sessions_col` with a server-issued
  `started_at` and `duration_minutes`. The client displays the
  remaining time, but the server is the source of truth.
- `auto_submit.py` background job sweeps every minute and force-
  submits any exam whose timer has expired; transitions state to
  `SUBMITTED` (Module 8 owns this transition — see ARCHITECTURE.md).
- Manual submit endpoint also re-checks server-side elapsed time
  before honoring the request.

---

## Module 9 — Input Validation

**Problem.** User-supplied JSON containing NoSQL operators (`$where`,
`$ne`, …) or HTML/JS (`<script>`, `onerror=`) leads to injection or
XSS once the value is reflected.

**Attack prevented.** NoSQL injection against Mongo queries; stored
XSS via answer text or exam metadata; oversized-payload DoS.

**How.**
- `validate_input()` scans request bodies recursively for NoSQL
  operators, XSS markers, oversized fields (>2 KB), and excessive
  nesting (>5 levels). `validation/service.py`.
- Phase 5.5 wires this in as a `@validate_body` decorator applied to
  every state-mutating route. A failed validation raises a 400 and
  emits a SECURITY-level log to the gateway for audit.

---

## Module 10 — Tab Monitoring

**Problem.** A student could open another tab or window during the
exam to consult prohibited material.

**Attack prevented.** Off-tab cheating (web search, AI tools, course
notes in another tab).

**How.**
- Frontend hook `useExamMonitoring.ts` listens for `visibilitychange`
  and `blur` events and POSTs to `/api/tab/event`.
- Backend stores in `tab_events_col` and exposes
  `GET /api/tab/risk-data` aggregating per-student tab-switch counts
  for Module 17 (§27.7 schema).

---

## Module 11 — Clipboard Monitoring

**Problem.** Copy/paste between the exam window and external sources
is a primary cheating channel for text-based answers.

**Attack prevented.** Paste-in of pre-prepared answers; copy-out of
question text to share with others.

**How.**
- Hook listens for `copy`/`paste`/`cut` events on the exam form and
  POSTs to `/api/clipboard/event`.
- `clipboard_events_col` is aggregated by `/api/clipboard/risk-data`
  for Module 17.

---

## Module 12 — Activity Logging

**Problem.** Without an immutable behavioral record of the session,
disputes about whether a student was active/idle, or whether they
attempted suspicious operations, cannot be settled.

**Attack prevented.** Repudiation by either student or system about
what happened during the exam.

**How.**
- Heartbeat every N seconds plus idle markers (`idle_time_seconds`)
  collected by `activity_events_col`.
- All cross-module log writes flow through the §27.3 Logging Gateway
  (`POST /api/logs/write`), never directly to `logs_col`. Each entry
  has a SHA-256 integrity hash; tampering detected by Module 13.

---

## Module 13 — Secure Logging

**Problem.** A privileged attacker (or anyone with DB access) could
edit log documents after the fact to cover their tracks.

**Attack prevented.** Log tampering by anyone who reaches the
database — including the legitimate operator.

**How.**
- Every log document carries an `integrity_hash =
  SHA256(sort_keys(json(content)))` computed at write time
  (`logging/service.py::_compute_integrity`).
- `GET /api/logs/verify/<log_id>` recomputes the hash for one entry.
- `GET /api/logs/verify` (Phase 5.1) recomputes over a whole window
  and reports every tampered entry, demonstrating the integrity claim
  is actually verifiable.
- Demo recipe: edit `details` of a log row directly in Mongo, hit
  `/api/logs/verify`, see the row flagged with mismatched
  `stored_hash` vs `computed_hash`.

---

## Module 14 — Multi-Session Detection

**Problem.** A student logs in twice — once from their own laptop,
once handing credentials to a friend — to get help.

**Attack prevented.** Concurrent use of one account.

**How.**
- Module 14 tracks open `session_id` values per user. When a second
  active session appears, the older one is flagged and the user is
  surfaced as multi-session.
- `multisession_attempts_col` is aggregated for Module 17 risk
  scoring (§27.7 metric `multi_session_attempts`).

---

## Module 15 — Behavioral Analysis

**Problem.** Pure event counts (tab switches, pastes) miss subtler
cheating patterns — answering 30 questions in 30 seconds is also
suspicious even with no tab switches.

**Attack prevented.** Pre-prepared answer dumps where a student
appears to "answer" instantly; bot-driven submission.

**How.**
- `behavioral/analyzer.py` flags `fast_answer` events where the
  per-question time is below a configured threshold.
- Counts surface as `fast_answer_count` in `/api/behavioral/risk-data`
  for Module 17.
- Phase 4 adds an "acceleration" rule: rate-of-rate spikes in
  fast-answer events within a sliding window.

---

## Module 16 — Answer Similarity Detection

**Problem.** Two students who collaborated will produce textually
similar answers even with question randomization in place.

**Attack prevented.** Collusion on text-answer questions.

**How.**
- TF-IDF + cosine similarity (`similarity/service.py`) per question
  across all student responses.
- Pair-level scores above a threshold are recorded in
  `similarity_results_col` and aggregated as a per-student
  `similarity_score` exposed at `/api/similarity/risk-data` for Module
  17.
- Reads `responses_col.answer_text`, which Module 6 now writes
  (Phase 1 schema unification).

---

## Module 17 — Risk Scoring & Dashboard

**Problem.** Individual signals (tab switches, paste counts,
similarity) are not actionable in isolation; a teacher needs a single
risk score per student.

**Attack prevented.** Decision paralysis from noisy raw signals; lets
graders focus on high-risk students first.

**How.**
- Weighted blend of the §27.7 metrics:
  `risk = 0.3·tab_switches + 0.2·idle_normalized + 0.3·similarity·10 + 0.2·fast_answers`
  bucketed into LOW/MEDIUM/HIGH (`risk/service.py::_compute_score`).
- Aggregation happens after the §27.4 transition into `ANALYZING`,
  via the dedicated `/risk-data` endpoints exposed by Modules 10, 11,
  12, 14, 15, 16 — never by direct DB reads (§27.7).
- Phase 1 fixed the deadlock that previously prevented the
  `SUBMITTED → ANALYZING → COMPLETED` cycle from ever completing.

---

## Cross-cutting integrity contract (PRD §27)

| Guarantee                       | Mechanism                                                       | Rubric line          |
|---|---|---|
| One JWT format, one issuer      | §27.1, Module 1 signs; all other modules verify via shared key  | Security, Integration |
| Consistent HTTP errors          | §27.2, shared exception envelope in `exceptions/handler.py`     | Concept, Integration  |
| No direct log writes            | §27.3, logging gateway is the sole writer of `logs_col`         | Security              |
| State machine enforcement       | §27.4, every state-sensitive endpoint checks `ExamState`        | Concept, Integration  |
| Per-module health               | §27.5, every module exposes `/health`; aggregator surfaces all 17 | Integration           |
| Refined ownership model         | §27.6 (this doc + ARCHITECTURE.md)                              | Integration           |
| Read-only risk aggregation      | §27.7, six `/risk-data` endpoints feed Module 17                | Integration           |
| Integration tests in CI         | §27.8, pytest suite at `backend/tests/`                         | Integration           |
