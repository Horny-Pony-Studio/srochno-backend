# Срочные Услуги - Backend API

Production-grade FastAPI backend for Telegram WebApp urgent services marketplace.

## 🎯 Core Features

- **Telegram WebApp Authentication** - Validates `initData` from Telegram Mini App SDK
- **Order CRUD** - 60-minute timer, edit/delete locks, contact protection
- **Payment System** - Balance management, transactions, 2₽ per order access
- **Race Condition Safe** - Database locks prevent double-spending and executor overflow
- **Review System** - Client ratings (1-5 stars) and executor complaints
- **Auto-Close Logic** - Expires orders after 60 min or 15 min no customer response

## 📋 Architecture

```
app/
├── api/           # FastAPI route handlers
│   ├── orders.py      # Order CRUD + take order
│   ├── users.py       # User profile & preferences
│   ├── balance.py     # Balance recharge
│   └── reviews.py     # Client reviews & executor complaints
├── core/          # Configuration & database
│   ├── config.py      # Pydantic settings
│   └── database.py    # SQLAlchemy async setup
├── models/        # SQLAlchemy ORM models
│   ├── user.py        # User (Telegram ID as PK)
│   ├── order.py       # Order + ExecutorTake
│   ├── balance.py     # BalanceTransaction
│   └── review.py      # ClientReview + ExecutorComplaint
├── schemas/       # Pydantic request/response models
│   ├── user.py
│   ├── order.py
│   ├── balance.py
│   └── review.py
├── services/      # Business logic layer
│   ├── order_service.py    # Order operations
│   ├── balance_service.py  # Payment operations
│   └── review_service.py   # Review operations
├── middleware/    # Auth & security
│   └── auth.py         # Telegram initData validation
├── utils/         # Utilities
│   └── timer.py        # Auto-close background task
└── main.py        # FastAPI app entry point

alembic/           # Database migrations
tests/             # Unit & integration tests
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Poetry (or pip)

### 2. Installation

```bash
# Clone repository
git clone <repo-url>
cd srochno-backend

# Install dependencies
poetry install
# OR
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Edit .env with your values
nano .env
```

### 3. Environment Configuration

```env
# Database
DATABASE_URL=postgresql+asyncpg://srochno:password@localhost:5432/srochno

# Telegram Bot Token (get from @BotFather)
TELEGRAM_BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here

# CORS (frontend URL)
CORS_ORIGINS=http://localhost:10002,https://your-webapp.com
```

### 4. Database Setup

```bash
# Create database
createdb srochno

# Run migrations
poetry run alembic upgrade head

# OR if using pip
alembic upgrade head
```

### 5. Run Development Server

```bash
# With Poetry
poetry run uvicorn app.main:app --reload --port 8000

# With pip
uvicorn app.main:app --reload --port 8000
```

API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## 📡 API Endpoints

### Authentication

All endpoints (except `/orders` GET listing) require Telegram WebApp authentication:

```http
Authorization: Bearer <initData>
```

Where `<initData>` is the raw string from Telegram SDK: `window.Telegram.WebApp.initData`

### Orders

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/orders` | ✅ | Create order (FREE) |
| `GET` | `/api/orders` | ❌ | List orders (public browsing) |
| `GET` | `/api/orders/{id}` | Optional | Get order (contact hidden unless paid) |
| `PUT` | `/api/orders/{id}` | ✅ | Update order (before taken, city locked) |
| `DELETE` | `/api/orders/{id}` | ✅ | Delete order (before taken) |
| `POST` | `/api/orders/{id}/take` | ✅ | Take order (costs 2₽) |

### Users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/users/me` | ✅ | Get profile (balance, stats, rating) |
| `PUT` | `/api/users/me/preferences` | ✅ | Update subscribed categories/cities |
| `PUT` | `/api/users/me/notification-settings` | ✅ | Update notification frequency |

### Balance

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/balance` | ✅ | Get current balance |
| `POST` | `/api/balance/recharge` | ✅ | Recharge balance (DEV MODE) |

### Reviews

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/reviews/client` | ✅ | Leave client review (1-5 stars) |
| `POST` | `/api/reviews/executor` | ✅ | Leave executor complaint |
| `GET` | `/api/reviews` | ❌ | List all reviews (filter by rating) |

## 🔐 Security

### Telegram WebApp Validation

Backend validates `initData` using HMAC-SHA256 according to [official Telegram docs](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app):

```python
# In middleware/auth.py
def validate_telegram_init_data(init_data: str, bot_token: str) -> dict:
    # 1. Parse initData query string
    # 2. Extract and verify hash
    # 3. Generate secret_key = HMAC-SHA256("WebAppData", bot_token)
    # 4. Calculate hash from data
    # 5. Compare hashes (constant-time comparison)
    # 6. Return user data if valid
```

### Payment Safety

- **Database Transactions**: All balance operations use `begin_nested()` savepoints
- **Row Locking**: `with_for_update()` prevents race conditions
- **Idempotency**: Duplicate "take order" requests return cached result
- **Audit Trail**: Every transaction logged in `balance_transactions` table

## ⏱️ Timer System

### Server-Authoritative

Orders have a **60-minute lifetime** from creation:

```python
# In services/order_service.py
expires_at = order.created_at + timedelta(minutes=60)
minutes_left = max(0, int((expires_at - now).total_seconds() / 60))
```

Frontend should sync with server time, but server is the source of truth.

### Auto-Close Background Task

Run periodically (every 1-5 minutes):

```bash
# Example cron job
*/5 * * * * cd /path/to/backend && poetry run python -c "from app.utils.timer import auto_close_expired_orders; from app.core.database import async_session_maker; import asyncio; asyncio.run(auto_close_expired_orders(async_session_maker()))"
```

Or use a proper task scheduler (Celery, APScheduler, etc).

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# With coverage
poetry run pytest --cov=app --cov-report=html

# Specific test file
poetry run pytest tests/test_orders.py -v
```

## 📦 Database Schema

### Key Entities

**User** (Telegram user ID as primary key)
- `id` (BigInt) - Telegram user ID
- `balance` (Int) - rubles
- `completed_orders_count` (Int)
- `average_rating` (Float)

**Order** (12-char random ID)
- `id` (String)
- `client_id` → User
- `category`, `description`, `city`, `contact`
- `status` (active, expired, deleted, closed_no_response, completed)
- `city_locked` (Boolean)
- `created_at`, `expires_in_minutes`

**ExecutorTake** (junction table)
- `order_id` → Order
- `executor_id` → User
- `taken_at` (timestamp)

**BalanceTransaction** (audit log)
- `user_id` → User
- `type` (recharge, order_take, refund)
- `amount` (Int, negative for deductions)
- `balance_after` (Int)

**ClientReview** + **ExecutorComplaint**
- 1 review per order per user
- Updates executor's `average_rating` automatically

## 🚧 Production Deployment

### 1. Environment Setup

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y postgresql python3.11 python3.11-venv

# Create production user
sudo useradd -m -s /bin/bash srochno
```

### 2. Database Configuration

```sql
-- Create production database
CREATE DATABASE srochno;
CREATE USER srochno WITH PASSWORD 'strong-password-here';
GRANT ALL PRIVILEGES ON DATABASE srochno TO srochno;
```

### 3. Application Setup

```bash
# Switch to application user
sudo su - srochno

# Clone repository
git clone <repo-url> app
cd app

# Install dependencies
poetry install --no-dev

# Configure environment
cp .env.example .env
nano .env  # Set production values

# Run migrations
poetry run alembic upgrade head
```

### 4. Systemd Service

Create `/etc/systemd/system/srochno-api.service`:

```ini
[Unit]
Description=Srochno API Service
After=network.target postgresql.service

[Service]
Type=notify
User=srochno
Group=srochno
WorkingDirectory=/home/srochno/app
Environment="PATH=/home/srochno/app/.venv/bin"
ExecStart=/home/srochno/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable srochno-api
sudo systemctl start srochno-api
sudo systemctl status srochno-api
```

### 5. Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.srochno.ru;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. SSL Certificate

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d api.srochno.ru
```

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
# {"status": "healthy"}
```

### Logs

```bash
# Systemd logs
sudo journalctl -u srochno-api -f

# Application logs (if configured)
tail -f /var/log/srochno/api.log
```

### Metrics

Consider integrating:
- **Prometheus** + **Grafana** for metrics
- **Sentry** for error tracking
- **New Relic** / **DataDog** for APM

## 🔧 Development

### Code Style

```bash
# Format code
poetry run black app tests

# Lint
poetry run ruff check app tests

# Type checking
poetry run mypy app
```

### Creating Migrations

```bash
# Auto-generate migration from model changes
poetry run alembic revision --autogenerate -m "Add new field to User"

# Review the generated migration in alembic/versions/

# Apply migration
poetry run alembic upgrade head
```

### Database Rollback

```bash
# Rollback last migration
poetry run alembic downgrade -1

# Rollback to specific revision
poetry run alembic downgrade <revision_id>
```

## 🐛 Troubleshooting

### Issue: "Invalid hash - data integrity check failed"

**Cause**: Telegram `initData` validation failed

**Solution**:
1. Verify `TELEGRAM_BOT_TOKEN` in `.env` matches your bot
2. Ensure frontend sends raw `initData` string, not parsed
3. Check initData hasn't expired (Telegram invalidates after ~1 hour)

### Issue: "Insufficient balance. Need 2₽"

**Cause**: Executor has insufficient funds

**Solution**:
```bash
# DEV MODE: Manually add balance via API
curl -X POST http://localhost:8000/api/balance/recharge \
  -H "Authorization: Bearer <initData>" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "method": "telegram_stars"}'
```

### Issue: "Maximum 3 executors reached"

**Cause**: Business rule - only 3 executors per order

**Solution**: This is expected behavior. Order is at capacity.

## 📝 TODO / Roadmap

- [ ] **Payment Integration**: Telegram Stars / YuKassa for real recharges
- [ ] **Telegram Bot**: Send notifications to subscribed executors
- [ ] **WebSocket**: Real-time order updates instead of polling
- [ ] **Admin Panel**: Moderate reviews, handle disputes
- [ ] **Analytics**: Dashboard with order completion rates, revenue
- [ ] **Rate Limiting**: Prevent abuse (e.g., 10 orders/hour per user)
- [ ] **Email Notifications**: For clients without Telegram
- [ ] **Geolocation**: Distance-based order filtering
- [ ] **Push Notifications**: PWA support for instant alerts

## 📄 License

Proprietary - All Rights Reserved

## 🤝 Contributing

Internal project - contact team lead for access.

---

**Built with ❤️ by ARCHITECT-9**

Need support? Contact: operator@srochno.ru
