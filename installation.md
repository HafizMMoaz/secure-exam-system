# Installation & Run

This document describes how to set up and run the Secure Online Examination System locally.

## Prerequisites

- Python 3.11+ installed
- Node.js 20+ and npm installed
- MongoDB running locally on `mongodb://localhost:27017`

## Backend Setup

1. Open a terminal in the project root.
2. Create and activate a Python virtual environment.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install backend dependencies.

```powershell
pip install -r requirements.txt
```

4. Create `backend/.env` or `cp backend/.env.example backend/.env` if it does not already exist and set values:

```env
FLASK_ENV=development
MONGO_URI=mongodb://localhost:27017/exam_security
JWT_SECRET=your_super_secret_key_change_this
JWT_EXPIRY_MINUTES=60
```

5. Start the Flask server.

```powershell
flask run
```

### Backend endpoints

You can generate a strong secret with the included tool:

```bash
python backend/tools/generate_jwt_secret.py --bytes 32 --format urlsafe
```

Copy the printed value into the `JWT_SECRET` field in `backend/.env`.

- API base: `http://127.0.0.1:5000`
- Swagger docs: `http://127.0.0.1:5000/api/docs`
- Health check: `http://127.0.0.1:5000/api/health`

## Frontend Setup

1. Open a second terminal in the project root.
2. Go to the frontend folder and install dependencies.

```powershell
cd frontend
npm install
```

3. Start the React development server.

```powershell
npm run dev
```

## Run Order

1. Start MongoDB locally.
2. Start the backend Flask server.
3. Start the frontend React app.
4. Open the frontend URL shown by Vite in the browser.

## Useful Checks

- Verify backend health: `GET /api/health`
- Verify authentication flow: login first, then call protected endpoints with `Authorization: Bearer <token>`
- Verify Swagger docs: open `/api/docs` and use the Authorize button with the Bearer token format
