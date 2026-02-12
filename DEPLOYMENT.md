# 🚀 Deployment Checklist

## Pre-Deployment

### 1. Environment Configuration
- [ ] Generate strong `SECRET_KEY`: `openssl rand -hex 32`
- [ ] Set production `DATABASE_URL` (PostgreSQL)
- [ ] Configure `TELEGRAM_BOT_TOKEN` from @BotFather
- [ ] Update `CORS_ORIGINS` with production frontend URL
- [ ] Set `DEBUG=False`

### 2. Database
- [ ] Create production PostgreSQL database
- [ ] Create database user with limited permissions
- [ ] Run migrations: `alembic upgrade head`
- [ ] Verify tables created: `\dt` in psql

### 3. Security Audit
- [ ] No sensitive data in `.env` committed to git
- [ ] `.gitignore` includes `.env`, `*.db`, `__pycache__`
- [ ] HTTPS enabled (SSL certificate)
- [ ] Firewall configured (only ports 80/443 exposed)
- [ ] PostgreSQL not publicly accessible

### 4. Testing
- [ ] Run test suite: `make test`
- [ ] Test Telegram initData validation with real data
- [ ] Verify payment transactions are atomic
- [ ] Test race condition: 3+ executors taking same order simultaneously
- [ ] Confirm timer expiry logic (wait 60+ minutes)

## Deployment Steps

### Option A: Docker (Recommended)

```bash
# 1. Clone repository
git clone <repo-url> /opt/srochno-backend
cd /opt/srochno-backend

# 2. Configure environment
cp .env.example .env
nano .env  # Set production values

# 3. Build and run
docker-compose up -d --build

# 4. Check logs
docker-compose logs -f api

# 5. Verify health
curl http://localhost:8000/health
```

### Option B: Systemd Service

```bash
# 1. Setup application user
sudo useradd -m -s /bin/bash srochno
sudo su - srochno

# 2. Install dependencies
git clone <repo-url> app
cd app
poetry install --no-dev

# 3. Configure environment
cp .env.example .env
nano .env

# 4. Run migrations
poetry run alembic upgrade head

# 5. Create systemd service (see README.md)
exit
sudo nano /etc/systemd/system/srochno-api.service

# 6. Start service
sudo systemctl enable srochno-api
sudo systemctl start srochno-api
```

### Option C: Cloud Platforms

#### Heroku
```bash
heroku create srochno-api
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set SECRET_KEY=$(openssl rand -hex 32)
git push heroku main
heroku run alembic upgrade head
```

#### Railway
1. Connect GitHub repository
2. Add PostgreSQL plugin
3. Set environment variables in dashboard
4. Deploy automatically on push

## Post-Deployment

### 1. Smoke Tests
```bash
# Health check
curl https://api.srochno.ru/health

# Create order (with valid Telegram initData)
curl -X POST https://api.srochno.ru/api/orders \
  -H "Authorization: Bearer <initData>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "Сантехника",
    "description": "СРОЧНО! Течет кран на кухне, нужен сантехник в течение часа. Район Центральный, возле метро Площадь Ленина.",
    "city": "Москва",
    "contact": "@ivan_123"
  }'

# List orders
curl https://api.srochno.ru/api/orders
```

### 2. Monitoring Setup
- [ ] Setup uptime monitoring (UptimeRobot, Pingdom)
- [ ] Configure error tracking (Sentry)
- [ ] Setup log aggregation (Papertrail, Loggly)
- [ ] Create alerting rules (Slack/Telegram notifications)

### 3. Background Tasks
- [ ] Setup cron job for auto-close orders (every 5 min)
- [ ] Configure Telegram bot for notifications (future)

### 4. Performance
- [ ] Enable PostgreSQL query logging
- [ ] Setup database connection pooling
- [ ] Configure uvicorn workers based on CPU cores
- [ ] Add Redis cache (optional, for future)

### 5. Backup
- [ ] Setup automated PostgreSQL backups (daily)
- [ ] Test restore procedure
- [ ] Store backups offsite (S3, Backblaze)

## Rollback Plan

### Database Rollback
```bash
# List migrations
alembic history

# Rollback to specific version
alembic downgrade <revision_id>
```

### Application Rollback
```bash
# Docker
docker-compose down
git checkout <previous-commit>
docker-compose up -d --build

# Systemd
sudo systemctl stop srochno-api
cd /home/srochno/app
git checkout <previous-commit>
poetry install --no-dev
sudo systemctl start srochno-api
```

## Troubleshooting

### "Database connection failed"
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection manually
psql -U srochno -d srochno -h localhost

# Verify DATABASE_URL in .env
```

### "Telegram initData validation failed"
```bash
# Verify bot token
curl https://api.telegram.org/bot<TOKEN>/getMe

# Check frontend sends raw initData string
console.log(window.Telegram.WebApp.initData)
```

### "Port 8000 already in use"
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

## Maintenance

### Update Dependencies
```bash
# Update all dependencies
poetry update

# Update specific package
poetry update fastapi

# Generate new requirements.txt
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

### Database Maintenance
```bash
# Vacuum database (reclaim space)
psql -U srochno -d srochno -c "VACUUM ANALYZE;"

# Check database size
psql -U srochno -d srochno -c "SELECT pg_size_pretty(pg_database_size('srochno'));"
```

## Production Checklist

Before announcing to users:

- [ ] API responds in <500ms (avg)
- [ ] Load test: 100+ concurrent users
- [ ] Payment transactions are atomic (verified)
- [ ] Timer accuracy within ±10 seconds
- [ ] All endpoints return proper HTTP status codes
- [ ] Error responses are user-friendly (no stack traces)
- [ ] CORS configured correctly (no wildcard in production)
- [ ] Rate limiting implemented (optional but recommended)
- [ ] API documentation accessible at /docs
- [ ] SSL certificate valid and auto-renewing
- [ ] Database backups running daily
- [ ] Monitoring alerts working
- [ ] Logs being collected and retained

