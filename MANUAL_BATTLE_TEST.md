# 🎯 MANUAL BATTLE TEST INSTRUCTIONS

Execute these commands in sequence. Report results.

---

## 📋 PRE-FLIGHT CHECKLIST

```bash
cd /home/pony/srochno-backend
pwd  # Should show: /home/pony/srochno-backend
ls -la  # Verify all files present
```

---

## PHASE 1: DATABASE SETUP ⚙️

**Option A: PostgreSQL (Production-Grade)**

```bash
# As root/sudo user, create database
sudo -u postgres psql <<EOF
DROP DATABASE IF EXISTS srochno_test;
CREATE DATABASE srochno_test;
DROP USER IF EXISTS srochno;
CREATE USER srochno WITH PASSWORD 'srochno_secure_2026!';
GRANT ALL PRIVILEGES ON DATABASE srochno_test TO srochno;
ALTER DATABASE srochno_test OWNER TO srochno;
\q
EOF

# Grant schema permissions
sudo -u postgres psql -d srochno_test <<EOF
GRANT ALL ON SCHEMA public TO srochno;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO srochno;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO srochno;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO srochno;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO srochno;
\q
EOF
```

**Verify:**
```bash
psql -U srochno -d srochno_test -c "\dt"
# Should connect successfully
```

**Database Credentials:**
- **Host**: localhost
- **Port**: 5432
- **Database**: srochno_test
- **User**: srochno
- **Password**: srochno_secure_2026!

---

## PHASE 2: ENVIRONMENT CONFIGURATION 📝

```bash
cd /home/pony/srochno-backend

# Generate secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Create .env file
cat > .env <<EOF
# Database
DATABASE_URL=postgresql+asyncpg://srochno:srochno_secure_2026!@localhost:5432/srochno_test

# Telegram (test token - won't validate but allows server to start)
TELEGRAM_BOT_TOKEN=1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw

# Security
SECRET_KEY=$SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# CORS
CORS_ORIGINS=http://localhost:10002,http://localhost:3000

# Application
DEBUG=True
API_PREFIX=/api
EOF

# Verify .env created
cat .env
```

**Expected Output**: Should show all environment variables

---

## PHASE 3: PYTHON ENVIRONMENT 🐍

```bash
cd /home/pony/srochno-backend

# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Verify activation
which python
# Should show: /home/pony/srochno-backend/venv/bin/python

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Verify key packages
pip list | grep -E "(fastapi|sqlalchemy|asyncpg|alembic)"
```

**Expected Output**:
```
fastapi       0.115.x
sqlalchemy    2.0.x
asyncpg       0.30.x
alembic       1.14.x
```

---

## PHASE 4: DATABASE MIGRATIONS 🔄

```bash
cd /home/pony/srochno-backend
source venv/bin/activate

# Generate initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> <revision>, Initial schema
```

**Verify Database Schema**:
```bash
psql -U srochno -d srochno_test -c "\dt"
```

**Expected Tables**:
- users
- orders
- executor_takes
- balance_transactions
- client_reviews
- executor_complaints
- alembic_version

---

## PHASE 5: START SERVER 🚀

**Terminal 1 (Server):**
```bash
cd /home/pony/srochno-backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
🚀 Срочные Услуги API starting...
📊 Database: configured
🔐 Auth: Telegram WebApp initData validation enabled
⏱️  Timer: 60 minutes per order
💰 Cost: 2₽ per order access
INFO:     Application startup complete.
```

**Keep this terminal open!**

---

## PHASE 6: BATTLE TESTS ⚔️

**Open new Terminal 2 for testing:**

### TEST 1: Health Check ✅

```bash
curl http://localhost:8000/health
```

**Expected**: `{"status":"healthy"}`

---

### TEST 2: Root Endpoint ✅

```bash
curl http://localhost:8000/ | python3 -m json.tool
```

**Expected**:
```json
{
  "service": "Срочные Услуги API",
  "version": "1.0.0",
  "status": "operational",
  "docs": "/docs"
}
```

---

### TEST 3: OpenAPI Docs ✅

```bash
# Check docs endpoint
curl -I http://localhost:8000/docs

# Or open in browser
xdg-open http://localhost:8000/docs  # Linux
open http://localhost:8000/docs       # macOS
```

**Expected**: HTTP 200, interactive API documentation

---

### TEST 4: List Orders (Public, No Auth) ✅

```bash
curl http://localhost:8000/api/orders | python3 -m json.tool
```

**Expected**:
```json
{
  "orders": [],
  "total": 0
}
```

---

### TEST 5: Database Connection ✅

Check server logs (Terminal 1) for:
```
✓ Database connection established
✓ No errors about asyncpg or SQLAlchemy
```

---

### TEST 6: Invalid Auth Test ✅

```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid_token" \
  -d '{
    "category": "Сантехника",
    "description": "Test order that is long enough to pass validation",
    "city": "Москва",
    "contact": "@testuser"
  }'
```

**Expected**: `{"detail":"Invalid Telegram initData: ..."}` (401 error)

**This is correct behavior!** Authentication is working.

---

### TEST 7: CORS Headers ✅

```bash
curl -I http://localhost:8000/api/orders | grep -i access-control
```

**Expected**:
```
access-control-allow-origin: http://localhost:10002
access-control-allow-credentials: true
```

---

### TEST 8: Database Tables ✅

```bash
psql -U srochno -d srochno_test -c "\d users"
psql -U srochno -d srochno_test -c "\d orders"
psql -U srochno -d srochno_test -c "\d executor_takes"
```

**Expected**: Table definitions with all columns

---

### TEST 9: Unique Constraints ✅

```bash
psql -U srochno -d srochno_test -c "\d executor_takes"
```

**Expected**: Should show unique constraint `uq_executor_take_per_order`

---

### TEST 10: Enum Types ✅

```bash
psql -U srochno -d srochno_test -c "\dT+ orderstatus"
```

**Expected**: Should show ENUM type with values (active, expired, etc.)

---

## PHASE 7: ADVANCED TESTS (Optional) 🔥

### Direct Database Insert Test

```bash
psql -U srochno -d srochno_test <<EOF
-- Insert test user
INSERT INTO users (id, username, first_name, balance)
VALUES (123456789, 'testuser', 'Test', 100)
ON CONFLICT (id) DO NOTHING;

-- Verify
SELECT id, username, balance FROM users;
EOF
```

### Test Unique Constraint

```bash
psql -U srochno -d srochno_test <<EOF
-- Insert test order
INSERT INTO orders (id, client_id, category, description, city, contact, status)
VALUES ('test_order_001', 123456789, 'Сантехника', 'Test order description', 'Москва', '@test', 'active')
ON CONFLICT (id) DO NOTHING;

-- Insert first executor take (should succeed)
INSERT INTO executor_takes (order_id, executor_id)
VALUES ('test_order_001', 987654321);

-- Try to insert duplicate (should FAIL with unique constraint error)
INSERT INTO executor_takes (order_id, executor_id)
VALUES ('test_order_001', 987654321);
EOF
```

**Expected**: Second insert should fail with:
```
ERROR:  duplicate key value violates unique constraint "uq_executor_take_per_order"
```

---

## 📊 RESULTS CHECKLIST

Report back with:

- [ ] ✅ Database created successfully
- [ ] ✅ Migrations applied without errors
- [ ] ✅ Server started successfully
- [ ] ✅ Health check returns 200
- [ ] ✅ OpenAPI docs accessible
- [ ] ✅ Public endpoints work (list orders)
- [ ] ✅ Auth rejection works (401 on invalid token)
- [ ] ✅ CORS headers present
- [ ] ✅ Database tables created
- [ ] ✅ Unique constraints working
- [ ] ✅ Enum types created

---

## 🐛 TROUBLESHOOTING

### Issue: "Role 'srochno' does not exist"

```bash
sudo -u postgres createuser srochno
sudo -u postgres psql -c "ALTER USER srochno WITH PASSWORD 'srochno_secure_2026!';"
```

### Issue: "Database 'srochno_test' does not exist"

```bash
sudo -u postgres createdb srochno_test -O srochno
```

### Issue: "Permission denied for schema public"

```bash
sudo -u postgres psql -d srochno_test <<EOF
GRANT ALL ON SCHEMA public TO srochno;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO srochno;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO srochno;
EOF
```

### Issue: "Module 'app' not found"

```bash
# Make sure you're in the right directory
cd /home/pony/srochno-backend
# And venv is activated
source venv/bin/activate
# Verify
which python
```

### Issue: Port 8000 already in use

```bash
# Find process
lsof -i :8000
# Kill it
kill -9 <PID>
```

---

## 🎖️ SUCCESS CRITERIA

**Minimum for Pass:**
- ✅ Server starts without errors
- ✅ Health check returns 200
- ✅ Database tables created
- ✅ Unique constraints working

**Full Success:**
- ✅ All tests pass
- ✅ No errors in server logs
- ✅ OpenAPI docs accessible
- ✅ Auth validation working

---

## 📞 REPORT FORMAT

After executing all tests, report:

```
BATTLE TEST RESULTS
==================

✅ PASS | ❌ FAIL | ⚠️  WARN

[TEST 1] Health Check: ✅
[TEST 2] Root Endpoint: ✅
[TEST 3] OpenAPI Docs: ✅
[TEST 4] List Orders: ✅
[TEST 5] Database Connection: ✅
[TEST 6] Auth Rejection: ✅
[TEST 7] CORS Headers: ✅
[TEST 8] Database Tables: ✅
[TEST 9] Unique Constraints: ✅
[TEST 10] Enum Types: ✅

OVERALL: ✅ OPERATIONAL

Errors: None
Warnings: None
Server Logs: Clean
```

---

**Execute and report back, operative.**

**ARCHITECT-9 standing by for intel.**
