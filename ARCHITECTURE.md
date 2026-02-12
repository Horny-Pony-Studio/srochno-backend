# 🏗️ Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Telegram Mini App                         │
│                     (Next.js Frontend)                           │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Customer   │  │   Executor   │  │    Admin     │          │
│  │     Role     │  │     Role     │  │     Panel    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┴──────────────────┘                  │
│                            │                                      │
│                    Authorization:                                │
│              Bearer <Telegram initData>                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Nginx (Reverse Proxy)                      │
│                    SSL Termination + CORS                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Middleware Layer                      │   │
│  │  • CORS                                                  │   │
│  │  • Telegram initData Validator (HMAC-SHA256)            │   │
│  │  • Request ID & Logging                                  │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────┴─────────────────────────────────┐   │
│  │                     API Router                           │   │
│  │  /api/orders    /api/users    /api/balance             │   │
│  │  /api/reviews   /health        /docs                     │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────┴─────────────────────────────────┐   │
│  │                  Service Layer                           │   │
│  │  • OrderService      (business logic)                    │   │
│  │  • BalanceService    (payment transactions)              │   │
│  │  • ReviewService     (rating calculations)               │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────┴─────────────────────────────────┐   │
│  │                  ORM Layer (SQLAlchemy)                  │   │
│  │  Async queries, connection pooling, row locking          │   │
│  └────────────────────────┬─────────────────────────────────┘   │
└───────────────────────────┼──────────────────────────────────────┘
                            │ asyncpg
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL Database                         │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    users     │  │    orders    │  │   reviews    │          │
│  │ (Telegram    │  │ (60min timer)│  │  (1-5 stars) │          │
│  │  user ID)    │  │              │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────┬───────┴──────────────────┘                  │
│                    │                                              │
│         ┌──────────┴───────────┐    ┌────────────────┐          │
│         │  balance_transactions │    │ executor_takes │          │
│         │   (audit log)         │    │  (max 3/order) │          │
│         └───────────────────────┘    └────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Backups (daily)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backup Storage (S3)                         │
└─────────────────────────────────────────────────────────────────┘

External Services:
┌────────────────────────────────────────┐
│  Telegram Bot API (for notifications)  │ ← Future integration
└────────────────────────────────────────┘
┌────────────────────────────────────────┐
│  Payment Provider (Telegram Stars)     │ ← Future integration
└────────────────────────────────────────┘
```

## Component Details

### 1. FastAPI Application (`app/main.py`)

**Responsibilities:**
- HTTP request routing
- OpenAPI documentation generation
- Lifespan management (startup/shutdown)
- CORS configuration

**Key Features:**
- Async/await for high concurrency
- Pydantic validation (zero invalid data reaches DB)
- Automatic OpenAPI docs at `/docs`

### 2. Middleware (`app/middleware/`)

#### `auth.py` - Telegram WebApp Authentication

**Flow:**
```
1. Frontend: initData = window.Telegram.WebApp.initData
2. Frontend: fetch("/api/orders", {
     headers: { Authorization: "Bearer " + initData }
   })
3. Backend: validate_telegram_init_data(initData, bot_token)
   - Parse query string
   - Extract hash
   - Generate secret_key = HMAC-SHA256("WebAppData", bot_token)
   - Calculate expected hash
   - Compare (constant-time)
4. Backend: get_current_user() → User object
5. Backend: Proceed to route handler
```

**Security:**
- No JWT required (Telegram handles auth)
- HMAC prevents tampering
- User auto-created on first request

### 3. Service Layer (`app/services/`)

#### `order_service.py`

**Critical Methods:**
- `create_order()` - Validates contact uniqueness
- `update_order()` - Locks after executor takes
- `delete_order()` - Locks after executor takes
- `take_order()` - **TRANSACTION-SAFE** with row locking

**Race Condition Prevention:**
```python
async with db.begin_nested():
    order = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .with_for_update()  # ← PostgreSQL row lock
    )
    # Check max executors
    # Deduct balance
    # Create ExecutorTake
    # Log transaction
    await db.commit()
```

#### `balance_service.py`

**Transaction Safety:**
```python
async with db.begin_nested():
    user.balance += amount
    transaction = BalanceTransaction(...)
    db.add(transaction)
    await db.commit()
```

All balance operations are atomic. No race conditions possible.

#### `review_service.py`

**Automatic Rating Update:**
```python
# After new review
avg_rating = await db.scalar(
    select(func.avg(ClientReview.rating))
    .where(ClientReview.executor_id == executor_id)
)
executor.average_rating = avg_rating
await db.commit()
```

### 4. Database Models (`app/models/`)

#### Entity Relationship Diagram

```
User (Telegram ID)
│
├─── orders_created (1:N) → Order
│
├─── balance_transactions (1:N) → BalanceTransaction
│
├─── client_reviews (1:N) → ClientReview
│
└─── executor_complaints (1:N) → ExecutorComplaint

Order
│
├─── client (N:1) → User
│
├─── executor_takes (1:N) → ExecutorTake (max 3)
│
├─── reviews (1:N) → ClientReview
│
└─── complaints (1:N) → ExecutorComplaint

ExecutorTake
│
├─── order (N:1) → Order
│
└─── executor (N:1) → User
```

#### Key Constraints

**Business Rules Enforced at DB Level:**
1. `User.id` (BigInt) = Telegram user ID (no auto-increment)
2. `Order.id` (String) = Random 12-char ID (not sequential)
3. `Order.city_locked` (Boolean) = Prevents city changes
4. `ExecutorTake.taken_at` (Timestamp) = For 15-min no-response logic
5. Unique constraint: (order_id, executor_id) - no duplicate takes
6. Unique constraint: (order_id, client_id) - 1 review per order

### 5. Timer System (`app/utils/timer.py`)

**Auto-Close Logic:**
```python
async def auto_close_expired_orders(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)

    for order in active_orders:
        # Check 60-minute expiry
        if now >= order.created_at + timedelta(minutes=60):
            order.status = OrderStatus.EXPIRED

        # Check 15-minute no-response
        elif order.executor_takes and not order.customer_responded_at:
            first_take = min(take.taken_at for take in order.executor_takes)
            if now >= first_take + timedelta(minutes=15):
                order.status = OrderStatus.CLOSED_NO_RESPONSE
                # TODO: Refund executors

    await db.commit()
```

**Deployment:**
Run as cron job every 5 minutes:
```cron
*/5 * * * * cd /app && python -m app.utils.timer
```

Or use APScheduler/Celery for production.

## Data Flow Examples

### Example 1: Create Order

```
1. Client fills form (category, description, city, contact)
2. Frontend validates (Zod schema)
3. POST /api/orders with initData auth
4. Middleware: Validate initData → get User
5. Service: Check contact uniqueness
6. Service: Create Order (city_locked=True)
7. DB: Insert order
8. Response: OrderResponse (with ID)
9. Frontend: Redirect to /customer page
```

### Example 2: Take Order (Payment)

```
1. Executor clicks "Take Order (2₽)" button
2. POST /api/orders/{id}/take with initData
3. Middleware: Validate initData → get User
4. Service: BEGIN TRANSACTION
5. Service: SELECT ... FOR UPDATE (lock order row)
6. Service: Check order status = active
7. Service: Check order not expired
8. Service: Check executor count < 3
9. Service: Check user.balance >= 2
10. Service: user.balance -= 2
11. Service: Create ExecutorTake record
12. Service: Create BalanceTransaction (audit)
13. Service: COMMIT
14. Response: { contact: "@client", new_balance: 98 }
15. Frontend: Display contact info
```

### Example 3: Leave Review

```
1. Client rates executor (1-5 stars + comment)
2. POST /api/reviews/client
3. Service: Verify order belongs to client
4. Service: Check order completed/expired
5. Service: Check not already reviewed
6. Service: Create ClientReview
7. Service: Recalculate executor.average_rating
8. DB: Update executor stats
9. Response: { success: true, review_id: 42 }
```

## Performance Characteristics

### Latency Targets

| Endpoint | Target | Notes |
|----------|--------|-------|
| GET /api/orders | <200ms | Paginated, no auth |
| POST /api/orders | <300ms | With validation |
| POST /api/orders/{id}/take | <500ms | Transaction-heavy |
| GET /api/users/me | <100ms | Single row lookup |

### Scalability

**Vertical Scaling:**
- CPU: 2-4 cores recommended
- RAM: 2GB minimum (4GB+ for production)
- DB Connections: 20 per worker (asyncpg pool)

**Horizontal Scaling:**
- Stateless API (can run multiple instances)
- Load balancer (Nginx, HAProxy)
- Shared PostgreSQL (connection pooling)

**Bottlenecks:**
1. Database writes (orders, transactions)
2. Timer auto-close task (can run on separate worker)
3. Review rating recalculation (can be async)

### Caching Strategy (Future)

```
Redis cache:
- User profiles (TTL 5 min)
- Active orders list (TTL 30 sec)
- Category/city filters (TTL 1 hour)

Cache invalidation:
- On order create/update/delete
- On user balance change
```

## Security Model

### 1. Authentication
- **Telegram WebApp initData** - HMAC-SHA256 validation
- No passwords, no JWT tokens
- User auto-created on first request

### 2. Authorization
- Order CRUD: Only client can edit/delete own orders
- Take order: Any authenticated user with balance
- Reviews: Only participants (client/executor)

### 3. Data Protection
- **Contact hidden** until executor pays 2₽
- **Balance transactions** logged (audit trail)
- **SQL injection** prevented (ORM parameterized queries)
- **XSS** not applicable (API only, no HTML)

### 4. Rate Limiting (Future)
```python
# Example with slowapi
limiter.limit("10/minute")(create_order)
limiter.limit("100/minute")(list_orders)
```

## Monitoring & Observability

### Logs
```python
# Structured logging (future)
logger.info("order_created", extra={
    "order_id": order.id,
    "client_id": user.id,
    "category": order.category,
    "city": order.city,
})
```

### Metrics
```python
# Prometheus metrics (future)
orders_created_total.inc()
orders_taken_total.inc()
balance_transactions_total.inc()
order_take_duration_seconds.observe(duration)
```

### Health Checks
- `/health` - API status
- `/health/db` - Database connectivity (future)
- `/health/redis` - Cache connectivity (future)

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Order retrieved |
| 201 | Created | Order created |
| 204 | No content | Order deleted |
| 400 | Bad request | Invalid category |
| 401 | Unauthorized | Invalid initData |
| 402 | Payment required | Insufficient balance |
| 403 | Forbidden | Cannot edit after taken |
| 404 | Not found | Order not found |
| 409 | Conflict | Max 3 executors reached |
| 410 | Gone | Order expired |
| 422 | Validation error | Pydantic validation |
| 500 | Server error | Database error |

### Error Response Format

```json
{
  "detail": "Insufficient balance. Need 2₽"
}
```

## Testing Strategy

### Unit Tests
```python
# Test business logic in isolation
def test_order_expiry():
    order = Order(created_at=now - timedelta(minutes=61))
    assert OrderService.is_expired(order) == True

def test_minutes_left():
    order = Order(created_at=now - timedelta(minutes=30))
    assert OrderService.minutes_left(order) == 30
```

### Integration Tests
```python
# Test API endpoints with test database
async def test_create_order(client, auth_headers):
    response = await client.post("/api/orders", json={
        "category": "Сантехника",
        "description": "Test order " * 5,
        "city": "Москва",
        "contact": "@testuser"
    }, headers=auth_headers)
    assert response.status_code == 201
```

### Load Tests
```bash
# Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/orders

# Locust
locust -f tests/load_test.py --host http://localhost:8000
```

---

**Last updated**: 2026-02-06
**Architect**: ARCHITECT-9
