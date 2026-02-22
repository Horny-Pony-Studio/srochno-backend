# Changelog

## v1.0.0-beta.7 (2026-02-22)

### Fixes
- **reviews**: Add `order_id`, `order_title`, `order_category` fields to `ReviewResponse` schema
- **reviews**: Fix `/mine` and `/about-me` endpoint semantics to correctly filter by reviewer vs. target user
- Accept `mainnet` as valid `CRYPTO_BOT_NETWORK` value

### CI/CD
- Remove `sudo` from deploy script
- Use `sudo` for `mkdir /opt/srochno-backend`
- Generate `.env` and `docker-compose.prod.yml` on deploy
- Use `vars.TELEGRAM_CHAT_ID` instead of secrets
- Use `vars` for `SSH_HOST` and `SSH_USER`

## v1.0.0-beta.4 (2026-02-15)

### Fixes
- **ci**: Revert `SSH_HOST` and `SSH_USER` from environment variables back to secrets — fixes deploy failure (`missing server host`)

## v1.0.0-beta.3 (2026-02-14)

### Features
- **Executor orders**: `GET /api/orders/my-executor` — list orders taken by the current executor
- **Review filtering**: filter reviews by rating, date range
- **Duplicate check**: prevent creating duplicate orders with the same parameters
- **Deep-link notifications**: Telegram deep-link support in order notifications

### Fixes
- Resolve all 36 mypy strict-mode errors across 35 source files
- Add `response_model=None` to `/health` endpoint to fix JSONResponse validation
- Align `payment_invoices.crypto_bot_invoice_id` DB constraint with model (unique constraint → unique index)

### Dependencies
- Update ruff `^0.8.0` → `^0.15.1`
- Update black `^24.10.0` → `^26.1.0`
- Update pytest-asyncio `^0.24.0` → `^1.3.0`
- Bump actions/setup-python from 5 to 6
- Bump minor-and-patch dependency group (11 updates)

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
