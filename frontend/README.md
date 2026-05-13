# Frontend — Secure Online Examination System

React + TypeScript + Vite client for the Secure Online Examination System.
Two top-level flows: student exam-taking and teacher dashboard.

## Run

```bash
npm install
npm run dev          # Vite dev server, default http://localhost:5173
```

The backend must be reachable at the URL configured in `src/api/client.ts`
(default `http://localhost:5500`). Start the backend first — see top-level
`installation.md`.

## Build & verify

```bash
npm run lint
npm run build        # production bundle into dist/
npm run preview      # serve the built bundle locally
```

## Layout

- `src/api/client.ts` — axios instance, JWT injection interceptor, base URL.
- `src/context/AuthContext.tsx` — login state, token persistence, role.
- `src/components/ProtectedRoute.tsx` — role-gated route wrapper.
- `src/pages/student/ExamPage.tsx` — student state machine (device registration
  → enrollment → activation → randomization → in-progress → submit).
- `src/pages/teacher/Dashboard.tsx` — exam CRUD, approvals, monitoring logs,
  risk dashboard.
- `src/hooks/useDeviceFingerprint.ts` — emits device fingerprint hash that the
  backend binds to the session JWT.
- `src/hooks/useExamMonitoring.ts` — heartbeat + tab/clipboard/activity
  event posters during `IN_PROGRESS`.

## Contract with the backend

This client follows the PRD §27 integration contract:
- Authorization header: `Bearer <jwt>` issued by Module 1 (Auth).
- Risk dashboard reads `data.students` (PRD §27.7 shape) with `scores` fallback.
- Metric keys: `tab_switch_count`, `fast_answer_count`, `idle_time_seconds`,
  `clipboard_paste_count`, `multi_session_attempts`, `similarity_score`.

See top-level `ARCHITECTURE.md` for the full module map.
