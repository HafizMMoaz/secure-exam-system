# Secure Exam System Wiki

Welcome to the secure-exam-system wiki!
Wikis provide a place in your repository to lay out the roadmap of your project, show the current status, and document software better, together.

## Overview
- **Project:** Secure Exam System
- **Purpose:** Provide a secure, monitored environment for delivering and grading exams with features like behavioral analysis, auto-submit, rate limiting, and WebSocket monitoring.

## Roadmap
- **Phase 1:** Core exam delivery and question management
- **Phase 2:** Authentication, RBAC, and session management
- **Phase 3:** Behavioral analysis and clipboard/device monitoring
- **Phase 4:** Randomization, similarity checks, and risk scoring
- **Phase 5:** Rate limiting, WebSocket monitoring, and production hardening

## Current Status
- Backend: Active development (Flask app in `backend/`)
- Frontend: Vite + React in `frontend/`
- Tests: Basic integration tests present in `backend/tests/`

## Getting Started (Developer)
1. Backend: `cd backend` then install requirements and run the app.
2. Frontend: `cd frontend` and run `npm install` then `npm run dev`.

See [installation.md](installation.md) for full setup steps.

## Contributing
- Read [contributing.md](contributing.md) for contribution guidelines.
- Open issues for bugs or feature requests and submit PRs against `main`.

## Contact
- Maintainers: see repository owners and contributors list.

---

If you'd like additional wiki pages (architecture, API reference, deployment, or runbook), tell me which pages to add and I'll create them.