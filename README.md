# 🎬 FastApiMovies

A production‑ready FastAPI application for browsing and purchasing movies with JWT authentication, filtering/search, shopping cart, orders, user profiles with avatar upload (S3/MinIO), email notifications (MailHog), Celery background jobs, and PostgreSQL + Alembic migrations.

- API base: `/api/v1`
- Interactive docs (OpenAPI): `http://localhost:8000/docs`


## ✨ Features
- 🔐 Authentication & accounts
  - Register/activate via email, login/logout, refresh tokens, change/reset password
  - JWT access/refresh with configurable TTL
- 🎥 Movies
  - CRUD for movies (create, read, update, delete)
  - Advanced filtering, sorting and pagination (fastapi-filter)
- 🛒 Shopping cart & 🧾 Orders
  - Add/remove items, checkout to create an order
  - Users can list/cancel their orders; admins see all orders with filters
- 👤 Profiles
  - Create user profile with avatar upload to S3-compatible storage (MinIO in dev)
- 📨 Notifications
  - Email templates (Jinja2) and async SMTP via MailHog in dev
- ⏱️ Background tasks
  - Celery worker/beat (Redis broker) with a maintenance task to clean expired activation tokens
- 🗄️ Database & migrations
  - PostgreSQL (dev/prod), Alembic migrations, seed data import on first run
  - SQLite in-memory in test mode
- 🐳 Dockerized stack for development, production and e2e tests


## 🧰 Prerequisites
- Docker Desktop (recommended) or local Python 3.10+
- Open local ports: 8000 (API), 5432 (PostgreSQL), 3333 (pgAdmin), 8025/1025 (MailHog), 9000/9001 (MinIO), 6379 (Redis)


## 🔌 Ports (defaults)
- API: http://localhost:8000
- MailHog UI/SMTP: http://localhost:8025 / smtp://localhost:1025
- MinIO API/Console: http://localhost:9000 / http://localhost:9001
- PostgreSQL: localhost:5432
- pgAdmin: http://localhost:3333
- Redis: localhost:6379


## 🧱 Tech Stack
- Python, FastAPI, Uvicorn/Gunicorn
- SQLAlchemy 2.x, Alembic, PostgreSQL (asyncpg)
- Pydantic, fastapi-filter
- aioboto3 (S3/MinIO), aiosmtplib (MailHog)
- Celery + Redis
- Docker Compose
- Testing: pytest, httpx, pytest-asyncio


## 🗂️ Project layout (high-level)
- `src/main.py` – FastAPI app, routers wiring
- `src/routes/*` – feature routers: accounts, movies, profiles, orders, shopping_cart
- `src/database/*` – DB models, sessions, migrations, seed
- `src/schemas/*` – Pydantic models
- `src/security/*` – JWT manager, helpers
- `src/notifications/*` – email sender and templates
- `src/storages/*` – S3 storage client
- `docker-compose-*.yml`, `Dockerfile`, `commands/*` – runtime/build scripts


## ⚙️ Configuration
Copy the example environment and adjust as needed:

```cmd
copy .env.sample .env
```

Key variables (see `.env.sample`):
- 🐘 Database: `POSTGRES_DB`, `POSTGRES_DB_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`
- 🔑 JWT: `SECRET_KEY_ACCESS`, `SECRET_KEY_REFRESH`, `JWT_SIGNING_ALGORITHM`
- 📨 Email/MailHog: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `MAILHOG_API_PORT`
- 🗃️ MinIO (S3-compatible): `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_HOST`, `MINIO_PORT`, `MINIO_STORAGE`
- 🧵 Celery/Redis: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

Notes:
- Runtime defaults live in `src/config/settings.py`.
- In Docker dev, internal hosts differ from localhost (e.g., `POSTGRES_HOST=postgres_theater`, MailHog: `mailhog_theater`, MinIO: `minio-theater`). Services are wired for you by Compose.
- The S3 endpoint in code defaults to AWS; in Docker dev, the MinIO bucket and credentials are prepared by the `minio_mc` service and URLs are accessible at `http://localhost:9000`. The storage client generates public links using the configured endpoint.


## 🚀 Quickstart (Docker dev)
This stack includes PostgreSQL, pgAdmin, backend (Uvicorn reload), migrator (Alembic + seed), MailHog, MinIO (+ bucket setup), Redis, Celery worker/beat.

```cmd
docker compose -f docker-compose-dev.yml up -d --build
```

- API: http://localhost:8000/docs
- MailHog UI: http://localhost:8025
- MinIO API/Console: http://localhost:9000 / http://localhost:9001
- pgAdmin: http://localhost:3333

The migrator service will:
- create migrations if needed and apply them,
- run the DB populate script (`database.populate`) to load initial seed data (CSV).

Logs and lifecycle:
```cmd
docker compose -f docker-compose-dev.yml logs -f web
docker compose -f docker-compose-dev.yml down
```

Default dev credentials (from `.env.sample` unless changed):
- pgAdmin: `PGADMIN_DEFAULT_EMAIL=admin@gmail.com`, `PGADMIN_DEFAULT_PASSWORD=admin`
- MinIO: `MINIO_ROOT_USER=minioadmin`, `MINIO_ROOT_PASSWORD=some_password`
- MailHog UI: no password by default (or set via env)


## 🐳 Run with Docker (other modes)

### Production (example compose)
```cmd
docker compose -f docker-compose-prod.yml up -d --build
```
- Backend runs with Gunicorn+Uvicorn workers
- Nginx example included (see `docker/nginx` and referenced config)

### End-to-end tests (Docker)
Runs a test container (pytest) against MailHog and MinIO test services; uses SQLite in-memory via `ENVIRONMENT=testing`.
```cmd
docker compose -f docker-compose-tests.yml up --build --abort-on-container-exit
```


## 💻 Local run without Docker (optional)
Docker is recommended. For quick exploration you can run API locally, but features that expect PostgreSQL/MinIO/MailHog will be limited.

1) Create and activate a virtual environment and install deps with Poetry:
```cmd
python -m pip install --upgrade pip
python -m pip install poetry
poetry install
```

2) Export minimal env (or copy `.env.sample` to `.env`). For a quick start with in-memory SQLite and test defaults:
```cmd
set ENVIRONMENT=testing
```

3) Run the app:
```cmd
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
Open http://localhost:8000/docs

Note: Using `ENVIRONMENT=testing` switches to SQLite in-memory DB and test email/storage defaults. For full functionality you’ll need PostgreSQL, MailHog and MinIO running (e.g., via Docker).


## 📚 API overview
The full, precise contract is available at `/docs`. High-level summary below (all endpoints are under `/api/v1` unless noted):

- 🔐 Accounts (`/accounts/`)
  - POST `/register/` – register a new user; sends activation email
  - POST `/resend-activation/` – resend activation email
  - POST `/activate/` – activate account with email+token
  - POST `/login/` – returns `access_token` and `refresh_token`
  - POST `/logout/` – invalidate refresh token (header: `refresh_token`)
  - POST `/refresh/` – issue new access token by refresh token
  - POST `/change-password/` – change password (auth required)
  - POST `/password-reset/request/` – request reset email
  - POST `/reset-password/complete/` – set a new password by token

- 🎥 Movies (`/movies/`)
  - GET `/` – list with filters: `year__gte`, `imdb__lte`, `genre_id`, `order_by`, `name__ilike`, pagination `page`, `per_page`
  - GET `/{id}` – details
  - POST `/` – create
  - PATCH `/{id}` – partial update
  - DELETE `/{id}` – delete

- 🛒 Shopping cart (`/cart/`)
  - GET `/` – current cart summary
  - POST `/add` – add movie by `movie_id`
  - DELETE `/remove/{movie_id}` – remove movie
  - POST `/checkout` – create pending order from cart

- 🧾 Orders (`/orders/`)
  - GET `/` – list current user orders (filters: `status`, `limit`, `offset`)
  - GET `/{order_id}` – order details (owner or admin)
  - PATCH `/{order_id}/cancel` – cancel pending order (owner/admin)

- 🛠️ Admin Orders (`/admin/orders/`)
  - GET `/` – admin list with filters (`user_id`, `status`, `date_from`, `date_to`, pagination)

- 👤 Profiles
  - POST `/users/{user_id}/profile/` – create profile (multipart form) with avatar uploaded to S3/MinIO


## 🔑 Authentication
- Put the access token into the header: `Authorization: Bearer <access_token>`
- Obtain tokens via `/accounts/login/` and refresh via `/accounts/refresh/`

Examples:

Login (get tokens):
```bash
curl -X POST http://localhost:8000/api/v1/accounts/login/ \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"user@example.com\",\"password\":\"StrongP@ssw0rd\"}"
```

Authorized request (list movies):
```bash
curl -X GET "http://localhost:8000/api/v1/movies/?page=1&per_page=10" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```


## 🗄️ Data & migrations
- Alembic is configured and invoked by the `migrator` service
- On first run, the DB is created/migrated and seeded from CSV files (`src/database/seed_data/*`)
- SQLAlchemy models live under `src/database/models/*`

Manual Alembic operations (inside dev container):
```bash
alembic -c /usr/src/alembic/alembic.ini revision --autogenerate -m "change"
alembic -c /usr/src/alembic/alembic.ini upgrade head
```


## ⏱️ Background jobs (Celery)
- Broker: Redis (`CELERY_BROKER_URL`), Result backend: Redis (`CELERY_RESULT_BACKEND`)
- Worker and Beat are part of the dev stack; an example task cleans expired activation tokens

Manual run (inside the dev container paths/scripts):
- Worker: `/commands/run_celery_worker.sh`
- Beat: `/commands/run_celery_beat.sh`


## 🧪 Testing
Run locally:
```cmd
pytest -m unit -q
pytest -m e2e -q
```

Via Docker (recommended for e2e):
```cmd
docker compose -f docker-compose-tests.yml up --build --abort-on-container-exit
```

Pytest config: `pytest.ini` sets `pythonpath=src`, `asyncio_mode=auto`, markers `unit`, `e2e`.


## 🧰 Development
- Lint/format/type-check (if installed via Poetry):
```cmd
flake8
isort .
black .
mypy src
```
- ENV switching: `ENVIRONMENT=testing` enables SQLite in-memory and test defaults


## ❗ Troubleshooting
- Web not reachable: ensure `web`, `db`, `migrator`, `minio`, and `mailhog` are healthy (`docker compose logs`)
- Emails not received: open MailHog UI (http://localhost:8025) and verify SMTP settings from `.env`
- S3 upload issues: verify MinIO is healthy, creds match `.env`, and bucket was created by `minio_mc` service
- DB migrations: check `alembic` logs in `migrator` service output
- Token errors: verify `SECRET_KEY_*` and `JWT_SIGNING_ALGORITHM` are consistent across services


## 📄 License
This project is provided as-is for educational purposes. Add your preferred license file if you plan to distribute.
