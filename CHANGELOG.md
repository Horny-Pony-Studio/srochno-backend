# Changelog

## v1.0.0-beta.2 (2026-02-13)

### CI/CD
- **ci.yml**: PR pipeline — lint (ruff), typecheck (mypy), tests (pytest), build check, Telegram notify
- **deploy.yml**: Tag pipeline — quality gate → Docker build → GHCR push → Trivy scan → SSH deploy
- **rollback.yml**: Manual workflow_dispatch to redeploy a previous image tag
- **dependabot-notify.yml**: Telegram notification on Dependabot PRs
- **dependabot.yml**: Weekly pip + github-actions dependency updates

### Fixes
- Fix all ruff lint errors: `from __future__ import annotations` in models, import sorting, unused imports
- Migrate ruff config to `[tool.ruff.lint]` section (fix deprecation)
- Add F821 to ruff ignore list (SQLAlchemy forward refs)

## v1.0.0-beta.1 (2026-02-13)

First beta release — backend API for Срочные Услуги Telegram WebApp.

### Features
- **Orders**: Create, take, complete, cancel urgent service orders with timer-based auto-close
- **Users**: Profile, notification settings, category/city preferences
- **Balance**: Top-up via CryptoPay, transaction history
- **Reviews**: Client reviews and executor complaints
- **Cities**: City dictionary endpoint
- **Auth**: Telegram WebApp initData (HMAC-SHA256) validation
- `GET /api/users/me/notification-settings` — retrieve saved notification settings
- `GET /api/users/me/preferences` — retrieve saved category/city preferences

### Infrastructure
- FastAPI async backend with SQLAlchemy 2.0 + asyncpg
- Alembic migrations
- Background timer loop for order expiration
- CORS middleware configured
