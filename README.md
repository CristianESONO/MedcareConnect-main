# MedCare Connect

MedCare Connect is a healthcare-services platform for finding medical services and providers, managing patient requests, and supporting healthcare organizations and practitioners.

## Architecture

- **Django backend** (`backend/`): authentication and sessions, permissions, business rules, API endpoints, Django admin, and pages that have not yet moved to React.
- **React frontend** (`frontend/`): the responsive single-page application, built with React, TypeScript, Vite, Tailwind CSS, and React Router.
- **Frontend delivery**: Vite builds the app into `backend/static/react/`. Django serves the React entry point for migrated routes; Django and WhiteNoise/Nginx serve static assets.
- **Shared assets and data**: Django static assets live in `backend/static/`; uploaded media lives in `media/`; project and catalogue reference material lives in `documents/`.
- **Deployment**: production can run Django/Gunicorn behind a system Nginx, or use the provided Dockerfile and Docker Compose configuration.

React does not replace Django's authentication or business logic. The browser uses Django's APIs and session cookies; some unmigrated routes still use Django templates.

## Requirements

- Python 3.12 (the Docker image uses Python 3.12)
- Node.js 22.12 or newer and npm (the Docker build uses Node.js 22)
- Git
- SQLite for local development, or PostgreSQL for production

## Local development

Run these commands from the repository root.

### 1. Set up Django

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py runserver
```

**Linux/macOS**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py runserver
```

Django listens at `http://127.0.0.1:8000`.

### 2. Run React in development mode

In a second terminal:

```bash
npm ci --prefix frontend
npm run dev --prefix frontend
```

Open `http://localhost:5173`. Vite proxies backend routes and APIs to Django on port 8000.

### 3. Build React for Django

```bash
npm ci --prefix frontend
npm run build --prefix frontend
python backend/manage.py collectstatic --noinput
```

The compiled entry point should exist at `backend/static/react/index.html`; Vite assets are placed alongside it. Django collects production assets into `staticfiles/`.

## Configuration

Django reads environment variables from the repository-root `.env` file when they are not already set by the process manager. Do not commit `.env` or put production credentials in source control.

For production, configure at least:

```dotenv
DEBUG=False
SECRET_KEY=<generate-a-unique-secret>
ALLOWED_HOSTS=app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com
HTTPS_ENABLED=True
TRUST_PROXY_HEADERS=True
```

Generate a secret locally on the server:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

By default, Django uses SQLite at the repository root. To use PostgreSQL, set `DATABASE_URL` to a value beginning with `postgres` and configure `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT`. Keep production environment files readable only by the service account.

## Tests and checks

```bash
python backend/manage.py check
python backend/manage.py test
npm run build --prefix frontend
npm run lint --prefix frontend
```

Optional browser/QA dependencies are listed in `backend/requirements-dev.txt`.

## Production deployment

For a systemd/Gunicorn server, update the code, build React, and then run the deployment script:

```bash
cd /usr/local/etc/MedcareConnect
git pull --ff-only origin main
npm ci --prefix frontend
npm run build --prefix frontend
bash backend/scripts/deploy_server_update.sh
```

The script installs Python requirements, applies migrations, collects static files, synchronizes the reference service catalogue, and restarts the `medcareconnect` systemd service. Build React before running it so the deployed Django app has the matching frontend bundle.

Because the Django project package is under `backend/`, a systemd unit should use that directory as its working directory. For example, a drop-in for `/usr/local/etc/MedcareConnect` can contain:

```ini
[Service]
WorkingDirectory=/usr/local/etc/MedcareConnect/backend
Environment="PYTHONPATH=/usr/local/etc/MedcareConnect/backend"
```

After changing a unit or drop-in, run `systemctl daemon-reload` and restart the service. Configure Nginx to proxy application routes to Gunicorn and serve `/static/` from the directory in `STATIC_ROOT` (`staticfiles/`). Keep the HTTPS and forwarded-proxy headers configured for the production domain.

For Docker:

```bash
docker compose up -d --build
```

Docker builds the React bundle as part of the `Dockerfile` and collects static assets when the web container starts. Configure the environment file expected by `docker-compose.yml` before starting the stack.

## Repository layout

```text
backend/       Django project, apps, migrations, tests, scripts, and Django static assets
frontend/      React + TypeScript SPA and Vite configuration
nginx/         Nginx configuration for the Docker deployment
documents/     Reference documents and project material
media/         User-uploaded files
```
