# Final Demo Script

A 10–12 minute walkthrough that exercises every security claim, every
§27 contract clause, and the §24 bonus features. Run in the order below.
Times in parentheses are budget guidance, not requirements.

## 0. Prerequisites (0:00 — before the viva starts)

```bash
# Backend + Mongo via podman:
podman network create exam-net
podman run -d --name exam-mongo --network exam-net -p 27017:27017 mongo:7
podman run -d --name exam-backend --network exam-net -p 5500:5500 \
  -v "$(pwd)/backend:/app:Z" -w /app \
  -e MONGO_URI=mongodb://exam-mongo:27017/exam_security \
  -e PORT=5500 -e BASE_URL=http://127.0.0.1:5500 \
  -e JWT_SECRET=demo_secret_change_in_prod -e FLASK_ENV=development \
  -e TIMEZONE=Asia/Karachi \
  python:3.11-slim bash -c \
  "pip install -q -r requirements.txt && python -m flask --app app run --host 0.0.0.0 --port 5500 --no-reload"

# Frontend:
cd frontend && npm install && npm run dev

# Populate demo data:
podman cp project-assessment/demo_seed.py exam-backend:/tmp/demo_seed.py
podman exec -e MONGO_URI=mongodb://exam-mongo:27017/exam_security \
            -e JWT_SECRET=demo_secret_change_in_prod \
            exam-backend python /tmp/demo_seed.py
```

Open `http://localhost:5173` in two browser windows side-by-side.

## 1. Authentication & MFA (1:00) — Module 1, 9, Module 5 RBAC

1. **Window A (teacher):** Log in as `teach_demo` / `demo_pass`.
   Show the network tab: a `POST /api/auth/otp/request` returns 200,
   then a `POST /api/auth/otp/verify` exchanges the 6-digit code for
   the JWT. Open the Logs tab — the `otp_issued` log entry is the
   dev-mode OTP delivery channel (PRD §27.3 + §11 MFA).
2. **Talking points:**
   - "Module 1 hashes the password with bcrypt; the DB dump never
     contains plaintext."
   - "MFA is two-step: Module 1 issues a one-time code, hashes it,
     stores it with a 5-min TTL, and delivers it through the §27.3
     logging gateway. In production the gateway would forward to SMS;
     in this build it stays on the gateway so the grader can see it."
   - "Module 9 (Input Validation) wraps the auth endpoints. Try
     submitting `{"username": {"$ne": null}}` — Module 9 catches the
     NoSQL operator key and returns 400 before pymongo sees it."

3. **Demo the rate limiter:** smash the login button 6+ times — the 6th
   attempt returns 429. Module 1 has flask-limiter on it at 5/min/IP.

## 2. Exam start: device, activation, timer (2:00) — Modules 3, 4, 8

1. **Window B (student):** Log in as `stud_demo` / `demo_pass`. The
   exam page first registers a device fingerprint (Module 3) before
   showing the exam list.
2. Pick "Demo Exam — Math" (it's in `ACTIVATION_VALID` state from the
   seed). Enter activation code `DEMO123` — backend transitions state
   to `IN_PROGRESS` and starts the server-side timer (Module 8).
3. **Talking points:**
   - "Module 3 binds the fingerprint hash into the JWT's
     `device_fingerprint_hash` claim. A second device for the same
     account would fail the device check."
   - "Module 8's timer is server-side. The client only renders elapsed
     time. The `auto_submit` background job catches anyone trying to
     dodge the deadline by closing the tab."

## 3. Monitoring (1:30) — Modules 10, 11, 12, 14, 15

1. **Window A:** Switch to the Risk tab on the teacher dashboard,
   select "Demo Exam — Math", click **Start live stream**. The badge
   flips to "Live: connected" (SSE).
2. **Window B (student):**
   - Open a second tab and switch back (Module 10 logs a tab_event).
   - Paste some text into the answer field (Module 11).
   - Sit idle for 15 seconds (Module 12 idle markers).
   - Answer two questions very fast in <5 seconds each (Module 15
     fast-answer + acceleration rule).
3. **Window A:** Live monitoring feed populates in real time. Point at
   each row — `tab_event`, `clipboard_event`, etc.
4. **Talking points:**
   - "Frontend monitoring hooks post each event to the matching
     module's endpoint; nothing writes to Mongo directly except the
     module that owns the collection (PRD §27.6, refined model in
     ARCHITECTURE.md)."
   - "The SSE stream at `/api/risk/stream/<exam_id>` is the §24
     bonus 'real-time monitoring' feature. Pure Flask, no extra
     dependency; uses an `_id` high-water mark to avoid replay."

## 4. Submit + risk analysis (1:30) — Modules 16, 17

1. **Window B:** Click **Submit** in the student window. The exam
   moves to `SUBMITTED`.
2. **Window A:** Click **Load Risk Scores** in the Risk tab. The
   backend transitions `SUBMITTED → ANALYZING`, aggregates the §27.7
   metrics from Modules 10/11/12/14/15/16, writes risk_scores docs,
   and transitions `ANALYZING → COMPLETED`. Risk-level cells are
   color-coded HIGH (red), MEDIUM (orange), LOW (green).
3. **Talking points:**
   - "Module 17's compute walks the §27.7 `/risk-data` endpoints —
     not direct DB reads — so each metric stays inside its owning
     module. The aggregator is a thin coordinator."
   - "Before Phase 1 the state machine was deadlocked at SUBMITTED.
     Module 17 needed ANALYZING but nothing transitioned there. Now
     the compute endpoint owns that transition."

## 5. Audit + integrity (1:30) — Module 13

1. **Window A:** Switch to the Logs tab. Show the integrity_hash on
   each log row.
2. Open a Mongo shell and tamper with one log row:
   ```bash
   podman exec exam-mongo mongosh exam_security --eval \
     "db.logs.updateOne({action:'exam_submitted'}, \
      {\$set:{details:{tampered:true}}})"
   ```
3. **Window A:** Hit `GET /api/logs/verify` (Swagger UI is at
   `/api/docs`). The tampered row surfaces with mismatched
   `stored_hash` vs `computed_hash`, and `all_intact: false`.
4. **Talking points:**
   - "Every log document carries SHA-256 over its content. Module 13
     is the only writer to the `logs` collection (PRD §27.3 gateway);
     every other module reaches it via HTTP. So integrity is provable
     end-to-end."

## 6. CI proof (0:30) — PRD §27.8

1. Open `.github/workflows/backend-test.yml` and the latest CI run on
   GitHub. Point at the green pytest step.
2. **Talking points:**
   - "Every PR runs the four §27.8 MUST-pass tests plus extras:
     expired-JWT → 401, log gateway round-trip, all 17 module health
     endpoints under 1 second, wrong-state action → 409. 31 cases
     total."

## 7. Architecture wrap-up (1:00)

1. Open `ARCHITECTURE.md` and walk the §27.6 ownership tables.
   Highlight that the PRD's collection-level rules are refined to
   per-state and per-field ownership, with rationale for each
   deviation.
2. Open `docs/security/per-module.md`. Show the three-question section
   for two or three of the more interesting modules (e.g. Module 13
   integrity, Module 16 TF-IDF similarity, Module 17 weighted blend).

## Closing checklist

| Claim | Where to point | What to say |
|---|---|---|
| Multi-factor auth | otp_issued log, OTP UI | "PRD §11 says MFA — we have it." |
| Rate limiting | 429 after 5 logins | "Credential stuffing mitigated." |
| Input validation | 400 on `$ne` injection | "Module 9 is wired, not isolated." |
| State machine | Risk dashboard after submit | "ANALYZING transition fixed." |
| Section 27.6 | ARCHITECTURE.md | "Refined model, every write justified." |
| Section 27.7 | /api/*/risk-data endpoints | "Module 17 reads only via gateways." |
| Section 27.8 | CI run | "Four MUST-pass tests, all green." |
| Section 24 bonus | Live feed in teacher view | "SSE stream + acceleration rule + color UI." |
| Log integrity | /api/logs/verify result | "SHA-256 integrity is verifiable." |
