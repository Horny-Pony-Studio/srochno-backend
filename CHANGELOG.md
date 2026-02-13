# Changelog

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
