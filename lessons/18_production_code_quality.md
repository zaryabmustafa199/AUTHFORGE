# Lesson 18: Production Code Quality & Error Handling

---

## The Problem: "It Works" ≠ "It's Good"

A function that works in the happy path is about 30% of the job. The other 70% is handling what happens when things go wrong:

- What if the database is down?
- What if Redis is unreachable?
- What if the email server rejects the connection?
- What if two users sign up with the same email at the exact same millisecond?

Without handling these cases, your API returns raw Python stack traces to clients — leaking internal code structure, file paths, library versions, and database connection strings. This is both a **security vulnerability** and a **terrible user experience**.

---

## 1. Structured Logging (Replacing `print()`)

### Why `print()` Is Bad

```python
# Before (bad):
print(f"User created: {user.id}")
# Output: User created: f1418b41-37a5-4715-a0e2-c3ca3001addc
```

Problems:
- No timestamp — when did this happen?
- No log level — is this an error, warning, or info?
- No module name — which file logged this?
- Not machine-parseable — can't search/filter/aggregate

### What We Built: JSON Structured Logging

```python
# After (good):
logger.info("User created", extra={"user_id": str(user.id), "email": user.email})
# Output:
# {"timestamp": "2026-05-18T21:07:09Z", "level": "INFO", 
#  "logger": "app.repositories.user_repo", "message": "User created",
#  "user_id": "f1418b41-...", "email": "testuser@example.com"}
```

Every log line is:
- **Timestamped** in UTC
- **Leveled** (DEBUG, INFO, WARNING, ERROR)
- **Sourced** (which module logged it)
- **JSON** (machine-parseable for log aggregation tools like ELK, Datadog, etc.)

### The `get_logger` Pattern

```python
# In any file:
from app.utils.logging import get_logger
logger = get_logger(__name__)

# __name__ = "repositories.user_repo"
# logger name = "app.repositories.user_repo"
```

This creates a hierarchy of loggers under the `app` namespace, so you can filter by module.

### Log Levels and When to Use Them

| Level | When to Use | Example |
|-------|------------|---------|
| `DEBUG` | Development-only detail | Token decoded, cache hit |
| `INFO` | Normal operations | User created, email sent, login successful |
| `WARNING` | Something unexpected but recoverable | Duplicate email attempt, blacklisted token used |
| `ERROR` | Something failed | DB unreachable, Redis error, email send failed |

---

## 2. Global Exception Handlers

### What They Are

FastAPI lets you register handlers that catch exceptions **before** they reach the client. Without them, any unhandled error returns:

```json
{
    "detail": "Internal Server Error"
}
```

...along with a Python traceback in the server logs that may leak to the client in development mode.

### What We Added to `main.py`

```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", extra={
        "path": request.url.path,
        "method": request.method,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."},
    )
```

Now the client always gets a clean JSON response. The full stack trace is logged server-side (for debugging) but never sent to the client (for security).

We also added a specific handler for `SQLAlchemyError` that returns 503 (Service Unavailable) — because a database error is usually temporary.

---

## 3. Exception Handling in Repositories (try/except + rollback)

### The Transaction Rollback Problem

```python
# DANGEROUS — no rollback:
async def create(self, user_in):
    self.session.add(user)
    await self.session.commit()   # ← If this fails, the session is in a broken state
    await self.session.refresh(user)  # ← This will also fail
    return user
```

If `commit()` fails (constraint violation, DB timeout, disk full), the SQLAlchemy session is left in a dirty state. Any subsequent operation on the same session will fail with "transaction is already aborted".

### The Fix: Explicit Rollback

```python
async def create(self, user_in):
    try:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    except IntegrityError as exc:
        await self.session.rollback()  # ← Clean up the broken transaction
        logger.warning("Duplicate email", extra={"email": user_in.email})
        raise  # Let the service layer handle the business logic
    except SQLAlchemyError as exc:
        await self.session.rollback()
        logger.error("DB error", extra={"error": str(exc)})
        raise
```

### Why We Catch `IntegrityError` Separately

`IntegrityError` means a database constraint was violated (duplicate email, foreign key doesn't exist, etc.). This is a **business logic error** — not a system failure. We log it as a `WARNING`, not an `ERROR`.

`SQLAlchemyError` catches everything else (connection failures, timeouts, etc.). These are **system failures** — logged as `ERROR`.

---

## 4. Fail-Closed vs. Fail-Open

When Redis is down and we can't check the token blacklist, should we:

- **Fail open**: Let the request through (assume token is valid)
- **Fail closed**: Reject the request (assume token is revoked)

We chose **fail closed**:

```python
async def is_blacklisted(self, jti: str) -> bool:
    try:
        return await self.redis.exists(f"blacklist:{jti}") > 0
    except RedisError:
        # Fail closed: if Redis is down, reject the token for safety
        return True
```

This means if Redis goes down, all API calls with tokens are rejected. This is the secure choice — a brief service disruption is better than letting potentially revoked tokens through.

---

## 5. Configurable CORS

### Before (Dangerous)

```python
allow_origins=["*"]  # Anyone from any domain can call our API
```

### After (Secure)

```python
# config.py
ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]  # Only our frontend

# main.py
app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS, ...)
```

In production, you'd set `ALLOWED_ORIGINS=["https://myapp.com"]` in the `.env` file. Only your frontend can make requests.

---

## 6. Security Headers Middleware

Every HTTP response now includes:

```
X-Content-Type-Options: nosniff       → Prevent MIME type sniffing attacks
X-Frame-Options: DENY                 → Prevent clickjacking (no iframe embedding)
X-XSS-Protection: 1; mode=block       → Enable browser XSS filter
Referrer-Policy: strict-origin-when-cross-origin  → Control referrer leakage
```

These are industry-standard security headers recommended by OWASP.

---

## 7. Celery Task Retries

### Before (No Retries)

If the email server is temporarily down, the task fails permanently. The user never gets their verification email.

### After (Exponential Backoff)

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_verification_email(self, email, otp):
    try:
        send_email_sync(...)
    except Exception as exc:
        # Retry after 10s, then 20s, then 40s (exponential backoff)
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))
```

`bind=True` gives the task access to `self`, which has the `.retry()` method. The `countdown` doubles each time (10 → 20 → 40 seconds), giving the email server time to recover.

---

## 8. Input Validation: Body() vs. Query Parameters

### Before (Weak)

```python
async def refresh_token(refresh_token: str):  # ← Any string, any length, as a query param
```

### After (Strict)

```python
async def refresh_token(refresh_token: str = Body(..., max_length=2048, embed=True)):
```

- `Body(...)`: The token must be in the request BODY (not the URL query string — which gets logged in server access logs!)
- `max_length=2048`: A JWT is never longer than ~2000 characters. This prevents someone from sending a 10MB string
- `embed=True`: Wraps it in a JSON object: `{"refresh_token": "..."}`

---

## Summary

| Issue Fixed | Before | After |
|------------|--------|-------|
| Logging | `print()` | Structured JSON with timestamps, levels, and extra fields |
| Global errors | Raw stack traces leaked to client | Clean JSON `{"detail": "..."}` response |
| DB failures | Unhandled crash, broken session | try/except + rollback + proper logging |
| Redis failures | Crash or silent failure | Fail closed (reject token) + service unavailable |
| CORS | `allow_origins=["*"]` | Configurable via `.env`, restricted by default |
| Security headers | None | X-Content-Type-Options, X-Frame-Options, etc. |
| Email retries | Single attempt, permanent failure | 3 retries with exponential backoff |
| Input validation | Bare query parameters | `Body(max_length=2048)` |
| Dead code | `pass` statements, dev comments | Removed |
