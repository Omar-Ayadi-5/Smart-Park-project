# Smart Park frontends

Two React/Vite applications share an Axios API client and a global loading indicator.

| Project | Vite root | Development port | Build output |
| --- | --- | --- | --- |
| Admin | `admin/src/` | 5173 | `admin/src/dist/` |
| Public | `public/src/` | 5174 | `public/src/dist/` |
| Shared package | `shared/` | Not standalone | Consumed by both apps |

## Requirements

Use Node.js 22.13+ and npm. The locked Vite version also supports Node.js 20.19+. Run the [Flask backend](../backend/README.md) against an initialized SQLite or PostgreSQL database for API-backed views.

## Install and configure

Run these commands from the repository root in PowerShell:

```powershell
Copy-Item frontend/admin/src/.env.example frontend/admin/src/.env
Copy-Item frontend/public/src/.env.example frontend/public/src/.env
npm --prefix frontend/admin run setup
npm --prefix frontend/public run setup
```

On macOS/Linux, use `cp` in place of `Copy-Item`. Setup installs dependencies for the selected application and the shared package. The shared package is a local `file:../../shared` dependency, resolved directly by the Vite alias.

Each app's `.env` file contains:

```dotenv
VITE_API_BASE_URL=http://localhost:5000/api
```

Include `/api` in the URL. If unset, the shared client defaults to the same local address. Never put JWT signing keys, database passwords, or private Supabase keys in a `VITE_*` variable: these values are public in the built JavaScript.

The `.env` file must be inside `admin/src/` or `public/src/`, not their parent folders. Restart Vite after changing it.

## Development

Start each frontend in its own terminal:

```shell
npm --prefix frontend/admin run dev
```

```shell
npm --prefix frontend/public run dev
```

Open `http://localhost:5173` for admin and `http://localhost:5174` for the public display. Both use strict ports. If a port is busy, stop the conflicting process or deliberately update the Vite configuration and backend `CORS_ORIGINS` together.

Register through the admin login page, then use the backend create-admin command to bootstrap the first super-admin. New registrations remain pending until approved.

## Build and inspect

From the repository root:

```shell
npm --prefix frontend/admin run build
npm --prefix frontend/public run build
npm --prefix frontend/admin run lint
npm --prefix frontend/public run lint
```

Preview either production build with its `preview` script. Vite preview is for local inspection, not a production hosting server.

## Hosting

For each site, use its `src/` folder as the Vite build root and deploy that folder's `dist/` output. Install `frontend/shared` as well as the application's dependencies; the complete repository layout must be available during the build.

Set `VITE_API_BASE_URL` in each site's build environment to your own HTTPS API URL, including `/api`. Vite embeds the value at build time, so changing it requires a rebuild. Configure the backend `CORS_ORIGINS` for both hosted origins. Avoid an HTTP API behind an HTTPS frontend because browsers block mixed content.

The admin app uses browser routes, so its host must rewrite unknown paths to `index.html`. An SPA `_redirects` file is included under `admin/src/public/` for hosts that support that convention. Other hosts need an equivalent fallback rule.

## Shared API behavior

`shared/services/api.jsx` attaches the browser's saved token to requests, serializes requests that use the global loading overlay, and clears the local session on HTTP 401. Tokens are stored in localStorage; review the session and XSS considerations in [SECURITY.md](../SECURITY.md).

## Troubleshooting

- **Connection refused:** confirm the backend is running and `VITE_API_BASE_URL` is correct.
- **CORS error:** include the exact frontend origin in the backend's `CORS_ORIGINS` and restart Flask.
- **403 after registration:** the account needs super-admin approval.
- **Missing shared module:** rerun the application's `setup` command with the full repository layout present.
- **404 on an admin page refresh:** configure the host's SPA fallback.
