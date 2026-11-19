# Security

This public source snapshot contains placeholder configuration only. Keep real `.env` files, device headers, database contents, and private keys outside version control. Credential rotation and any cleanup of separate development repositories are external operational tasks.

## Implemented controls

- Password hashing with Werkzeug; bounded JSON payloads and server-side credential validation.
- Uniform invalid-login responses and authentication rate limits (10 login / 5 registration attempts per minute per socket IP).
- Signed, expiring JWTs with current database checks for account existence, approval, and role. Deleting, unapproving, or demoting an account takes effect on its next request.
- Exact configurable browser CORS origins and debug mode disabled by default.
- Generic client errors with server-side exception logging.
- Device-scoped Supabase RPC authorization, row locking, idempotent history updates, and preservation of maintenance status.
- CA-verified TLS and clock checks in firmware; no certificate bypass.
- Automated backend, browser, lint/build, dependency, and firmware checks in CI.

## Deployment responsibilities

Use unique random backend keys, HTTPS, a trusted server database role, and an external Redis rate-limit store for multiple workers. Configure proxy/IP handling deliberately. CORS is a browser policy, not an authorization mechanism.

`VITE_*` settings are public browser configuration. Never put database passwords, private tokens, or server signing keys in them. Supabase publishable keys must be paired with narrowly scoped device authentication and database permissions; never distribute service-role keys to browsers or devices.

Browser JWTs currently use localStorage and last up to 24 hours. Protect against XSS with appropriate hosting headers and controlled dependencies. Logout clears the local browser session; it does not revoke a copied JWT individually. Account-level revocation is immediate through current-account checks. A production session design can add per-token revocation or move to secure HTTP-only cookies with CSRF protection.

`memory://` rate limiting is a single-process development default. Device credentials can be extracted from physically accessible firmware; provision separate identities and rotate/revoke them if compromised. CA roots and provider authentication settings require ongoing maintenance.

## Testing boundaries

Database tests create and drop tables. `TEST_DATABASE_URL` must identify a disposable database. Demo screenshots and recordings are synthetic and do not prove production capacity or physical sensor accuracy. Hardware compilation verifies build compatibility; real-world behavior requires bench testing.

## Reporting

Do not put credentials, customer data, or exploit details in public issues. Contact the repository owner privately with a redacted reproduction and the affected component.
