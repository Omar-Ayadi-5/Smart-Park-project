# Smart Park API

Flask, SQLAlchemy, Alembic, and HS256 JWT authentication. SQLite supports the local web demo; PostgreSQL supports the complete sensor integration.

## Install and configure

From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

On macOS/Linux use `source .venv/bin/activate` and `cp .env.example .env`.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | `sqlite:///smartpark.db` for a local demo, or your PostgreSQL connection URI |
| `SECRET_KEY` | Required random key of at least 32 characters; generate with `secrets.token_hex(32)` |
| `CORS_ORIGINS` | Comma-separated exact origins; defaults to localhost ports 5173 and 5174 |
| `FLASK_DEBUG` | `0` by default; enable only for local development |
| `RATELIMIT_STORAGE_URI` | `memory://` for one local process; shared `redis://...` for production workers |

The app loads `backend/.env`; host environment variables take precedence. Never use example placeholders as real secrets. URL-encode database password characters in connection strings. SQLite relative paths resolve under Flask's ignored `backend/instance/` folder.

## Database and first administrator

For PostgreSQL, create an empty database first. Apply the included migrations and optionally populate synthetic data:

```shell
python -m flask --app app:create_app db upgrade
python -m flask --app app:create_app seed-demo
python -m flask --app app:create_app create-admin
python run.py
```

The admin command prompts for credentials without echoing the password. It creates an approved super-admin and refuses to overwrite an existing account. New accounts registered through the frontend remain pending until approved. No default credentials are shipped.

`seed-demo` is idempotent and skips databases that already contain spots. It is intended for development. Migrations are explicit and never execute on application startup. This baseline targets a fresh database; adopting an existing database requires a schema comparison and a reviewed migration/stamp plan, not blindly running the initial migration.

For a model change, generate and review a migration before committing it:

```shell
python -m flask --app app:create_app db migrate -m "Describe the schema change"
python -m flask --app app:create_app db upgrade
python -m flask --app app:create_app db check
```

PostgreSQL migrations also install the sensor RPC and enable RLS on application tables. The backend database connection must use a trusted owner/server role; browser and device roles have no direct table access.

## API reference

Paths are relative to `/api`; requests and responses are JSON.

| Method | Path | Access |
| --- | --- | --- |
| GET | `/parking/dashboard` | Public |
| POST | `/admin/register` | Public, 5 attempts per minute per IP |
| POST | `/admin/login` | Approved accounts, 10 attempts per minute per IP |
| GET | `/admin/dashboard` | Approved admin |
| PUT | `/admin/update-username` | Current account |
| DELETE | `/admin/delete-account` | Current account |
| GET | `/admin/get-admins` | Admin or super-admin |
| PUT | `/admin/approve-admin/<id>` | Super-admin |
| DELETE | `/admin/delete-admin/<id>` | Super-admin |
| PATCH | `/admin/spot/<spot_id>/toggle-oos` | Admin or super-admin |

Registration uses `email`, `username`, and `password`; login uses `email` and `password`; username updates use `username`. Usernames are 3-50 characters and passwords 8-128 characters on the server. Payloads are limited to 16 KiB. Existing registration emails receive the same response as new ones; invalid login credentials receive a uniform response.

Protected requests use `Authorization: Bearer <token>`. JWTs expire after 24 hours; account existence, approval, and role are rechecked on every request. Occupied spots cannot be put out of service manually. Status updates and history entries are committed together. Internal exceptions are logged server-side and return a generic error response.

## Tests and dependencies

```shell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use SQLite unless `TEST_DATABASE_URL` identifies a disposable PostgreSQL test database. They create/drop application tables, so never point this setting at a shared or production database. PostgreSQL tests verify device mapping, idempotence, and maintenance preservation. CI also exercises migration upgrade/check/downgrade.

`requirements.in` contains direct runtime dependencies; `requirements.txt` locks their resolved dependency tree. To update: install `requirements.in` in an isolated environment, run `python lock_requirements.py`, then run tests and `pip-audit -r requirements.txt` before committing both files.

## Production

From `backend/` on Linux:

```shell
gunicorn --bind 0.0.0.0:5000 'app:create_app()'
```

Use your host's port, HTTPS, a private PostgreSQL server role, a unique signing key, exact frontend CORS origins, `FLASK_DEBUG=0`, and a shared Redis rate-limit store. The client IP comes from the socket; configure trusted proxy handling at the hosting boundary rather than accepting arbitrary forwarded IP headers. Gunicorn is not the Windows local development server.

See [hardware provisioning](IOT.md), [frontend hosting](../frontend/README.md), and [security notes](../SECURITY.md).
