# srochno-backend

FastAPI backend for **Срочные Услуги** — Telegram WebApp marketplace for urgent services.

## Stack

- Python 3.10+, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL
- Auth via Telegram WebApp `initData` (HMAC-SHA256)
- Alembic migrations, Pydantic v2

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in TELEGRAM_BOT_TOKEN, SECRET_KEY, DATABASE_URL

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Or with Docker:

```bash
cp .env.example .env
docker-compose up -d
```

API docs: http://localhost:8000/docs

## API

All endpoints except `GET /api/orders` require auth:
```
Authorization: Bearer <Telegram initData>
```

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| `POST` | `/api/orders` | + | Create order |
| `GET` | `/api/orders` | - | List orders |
| `GET` | `/api/orders/{id}` | ? | Get order (contact hidden unless paid) |
| `PUT` | `/api/orders/{id}` | + | Update order (before taken) |
| `DELETE` | `/api/orders/{id}` | + | Delete order (before taken) |
| `POST` | `/api/orders/{id}/take` | + | Take order (costs 2 RUB) |
| `GET` | `/api/users/me` | + | Profile |
| `PUT` | `/api/users/me/preferences` | + | Update subscribed categories/cities |
| `PUT` | `/api/users/me/notification-settings` | + | Update notification frequency |
| `GET` | `/api/balance` | + | Get balance |
| `POST` | `/api/balance/recharge` | + | Recharge balance |
| `POST` | `/api/reviews/client` | + | Leave review (1-5 stars) |
| `POST` | `/api/reviews/executor` | + | Leave complaint |
| `GET` | `/api/reviews` | - | List reviews |

## Project structure

```
app/
├── api/           Route handlers
├── core/          Config, database
├── middleware/     Telegram auth
├── models/        SQLAlchemy ORM
├── schemas/       Pydantic models
├── services/      Business logic
├── utils/         Timer auto-close
└── main.py
alembic/           Migrations
```

## Key mechanics

- **60-min order lifetime**, server-authoritative timer
- **Pay-to-reveal contacts** — executor pays 2 RUB to see client's contact
- **Max 3 executors** per order, enforced at DB level
- **Race-condition safe** — `SELECT ... FOR UPDATE` on balance operations
- **Auto-close** — expired orders + 15 min no-response

## Docs

- [Architecture](ARCHITECTURE.md) — system design, data flow, ER diagram
- [Deployment](DEPLOYMENT.md) — production checklist
- [Frontend Integration](FRONTEND_INTEGRATION.md) — API client, TypeScript types, React Query examples

## License

Proprietary
