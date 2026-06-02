# Contributing

Follow these steps to clone the repo, run the project locally, develop on a feature branch, test, and push:
Read [Exanple Routes](./backend/EXAMPLE_routes.py)
Read [SWAGGER TEMPLATES](./backend/SWAGGER_TEMPLATES.py)

## Development Options

You can work in either of these modes:

- Dockerized development using `docker compose up`
- Manual development using a local Python and Node.js setup

The Docker path is the recommended default because it brings up MongoDB, the backend, and the frontend with one command. Add `--build` only when you changed Dockerfiles or dependencies and want Compose to rebuild the images.

1) Clone the repository

```powershell
git clone https://github.com/HafizMMoaz/secure-exam-system.git
cd secure-exam-system
```

2) Choose your development environment

Dockerized development:

```powershell
docker compose up
```

Manual development:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
pip install -r requirements-test.txt   # for running the PRD §27.8 tests
```

3) Configure environment and start required services

Dockerized development uses the environment defined in [docker-compose.yml](./docker-compose.yml).

Manual development:

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

If you use Docker instead, the backend and frontend are started by Compose, so you do not need to run `flask run` or `npm run dev` manually.

4) Create a new working branch

```powershell
git checkout -b feature/your-descriptive-name
```

5) Make changes and run tests locally before committing or pushing

- Edit code in `backend/modules/...` or other files.
- Run the PRD §27.8 integration test suite before you push. It expects a
  running backend on `BASE_URL` (default `http://127.0.0.1:5500`) and the
  same MongoDB the backend uses.

If you are using Dockerized development, make sure the stack is already up before running tests. Use `--build` only if you changed container images:

```powershell
docker compose up -d
cd backend
python -m pytest tests/ -v
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
- When using Docker, rebuild with `docker compose up --build` after changing dependencies or Dockerfiles; otherwise `docker compose up` is enough.
