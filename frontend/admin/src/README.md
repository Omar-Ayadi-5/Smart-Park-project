# Smart Park admin application

React/Vite interface for approved parking administrators. It includes occupancy analytics, parking availability controls, account settings, and super-admin account approval and deletion.

## Run from the repository root

```powershell
Copy-Item frontend/admin/src/.env.example frontend/admin/src/.env
npm --prefix frontend/admin run setup
npm --prefix frontend/admin run dev
```

Open `http://localhost:5173`. Set `VITE_API_BASE_URL` in this directory's `.env` to your backend URL, including `/api`. The default is `http://localhost:5000/api`.

## Routes

| Route | View |
| --- | --- |
| `/` | Login and registration |
| `/admin/dashboard` | Occupancy dashboard and charts |
| `/admin/zones` | Parking availability and out-of-service controls |
| `/admin/users` | Administrator list and super-admin actions |
| `/admin/settings` | Account settings and sign-out |

UI visibility reflects the saved role; the backend enforces authorization. New accounts require approval before login. Follow the [backend setup guide](../../../backend/README.md#database-and-first-administrator) to create the first super-admin with the CLI.

Run `npm --prefix frontend/admin run build` or `npm --prefix frontend/admin run lint` from the repository root. The build output is this directory's `dist/` folder. Hosting needs a fallback to `index.html` for browser routes.

See the [frontend guide](../../README.md) for Node.js requirements, shared dependencies, hosting, and troubleshooting.
