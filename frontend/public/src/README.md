# Smart Park public display

React/Vite view of parking availability. It displays free, occupied, and out-of-service spaces without requiring an account.

## Run from the repository root

```powershell
Copy-Item frontend/public/src/.env.example frontend/public/src/.env
npm --prefix frontend/public run setup
npm --prefix frontend/public run dev
```

Open `http://localhost:5174`. Set `VITE_API_BASE_URL` in this directory's `.env` to your backend URL, including `/api`; the default is `http://localhost:5000/api`. The API must have parking zones and spots before the layout can show useful data. Spot prefixes `A` and `B` determine the two displayed columns.

Run `npm --prefix frontend/public run build` or `npm --prefix frontend/public run lint` from the repository root. Build output is this directory's `dist/` folder.

See the [frontend guide](../../README.md) for requirements, shared dependencies, configuration, and hosting.
