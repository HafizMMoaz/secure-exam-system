# Contributing

Follow these steps to clone the repo, run the project locally, develop on a feature branch, test, and push:

1) Clone the repository

```powershell
git clone https://github.com/HafizMMoaz/secure-exam-system.git
cd secure-exam-system
```

2) Create and activate a Python virtual environment and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

3) Configure environment and start required services

- Copy the example env file and edit it:

```powershell
Copy-Item .env.example .env
# Edit .env to set MONGO_URI, JWT_SECRET, JWT_EXPIRY_MINUTES, etc.
```

- Generate a secure `JWT_SECRET` and add it to `backend/.env` before running the app:

```powershell
python backend/tools/generate_jwt_secret.py --bytes 32 --format urlsafe
# Copy the printed secret into the JWT_SECRET entry in backend/.env
``` 

- Ensure MongoDB is running. Using Docker (example):

```powershell
docker run -d --name mongo -p 27017:27017 mongo:6
```

- Start the Flask app (project entrypoint is `backend/app.py`):

```powershell
flask run
```

4) Create a new working branch

```powershell
git checkout -b feature/your-descriptive-name
```

5) Make changes and run tests locally before committing or pushing

- Edit code in `backend/modules/...` or other files.
- Run unit tests and verification checks before you push:

```powershell
pytest
```

- If you changed the frontend, also run:

```powershell
cd frontend
npm run lint
npm run build
```

- Smoke-test endpoints using curl, Postman, or an HTTP client.

6) Commit and push your branch only after all tests pass

```powershell
git add .
git commit -m "Add feature: short description"
git push -u origin feature/your-descriptive-name
```

7) Verify on CI / create PR

- Open a Pull Request on your Git host and run CI/tests.
- Fix any failures and push additional commits to the same branch.

8) Merge to `main` after verification

Prefer merging via the Pull Request UI once checks pass. To merge locally:

```powershell
git checkout main
git pull origin main
git merge --no-ff feature/your-descriptive-name
git push origin main
```

9) Cleanup (optional)

```powershell
git branch -d feature/your-descriptive-name
git push origin --delete feature/your-descriptive-name
```

Notes
- The repository URL for this project is `https://github.com/HafizMMoaz/secure-exam-system.git`.
- Use `Copy-Item .env.example .env` to avoid overwriting an existing `.env`.
- If this project has a different test command, use that instead of `pytest`.
