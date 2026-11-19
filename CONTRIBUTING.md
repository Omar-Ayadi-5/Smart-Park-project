# Contributing

Read the component setup guides before changing the API, browser apps, or firmware. Keep changes focused and explain the behavior and validation in pull requests.

Before submitting, run the backend regression tests, both frontend lint/build commands, and dependency audits. For database changes, include and review an Alembic migration, check a fresh upgrade, and use a disposable database for rollback tests. For firmware changes, compile the canonical sketch and describe which real hardware checks were performed.

Use synthetic data in tests, screenshots, and recordings. Never commit `.env`, `iot_secrets.h`, secrets, node_modules, compiled Python files, or build outputs. Changes to configuration should update the corresponding example file and documentation.
