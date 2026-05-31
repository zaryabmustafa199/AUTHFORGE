# Lesson 12: Redis, TTL & Token Blacklisting

---

## What is Redis?

**Redis** (Remote Dictionary Server) is an in-memory data store. Everything is stored in RAM (not on disk), which makes it extremely fast — it can handle millions of operations per second.

Think of it as a giant Python dictionary that:
- Lives on its own server
- Persists across requests (unlike a Python variable)
- Has a built-in timer (TTL) on keys
- Can be shared across multiple server processes

```python
# Redis is essentially this, but networked and persistent:
redis_store = {
    "blacklist:uuid1": "1",
    "verify:user-uuid": "hashed_otp",
    "email_cooldown:user-uuid": "1",
}
```

---

## Why Not Just Use a Database?

| Operation | PostgreSQL | Redis |
|-----------|-----------|-------|
| Simple key lookup | ~5-10ms | ~0.1ms |
| Set a key | ~10ms | ~0.1ms |
| Auto-expire a key | ❌ (need a cron job) | ✅ Built-in TTL |
| Pub/Sub messaging | ❌ | ✅ |

Redis is 50-100x faster than PostgreSQL for simple key-value operations because:
1. Everything is in RAM (no disk I/O)
2. Operations are O(1) (constant time)
3. Single-threaded event loop (no locking overhead)

---

## What is TTL?

**TTL** = Time To Live. A countdown timer on a Redis key. When it hits zero, the key is automatically deleted.

```python
# Set a key with TTL:
await redis.setex("blacklist:abc123", 900, "1")
#                                    ↑
#                                  900 seconds = 15 minutes
#                                  After 15 min, key is automatically deleted

# Or separately:
await redis.set("blacklist:abc123", "1")
await redis.expire("blacklist:abc123", 900)
```

**Why TTL is genius**: You never have to write cleanup code. Redis handles it automatically. The key just disappears when it's no longer relevant.

---

## Token Blacklisting with Redis

**The Problem**: JWTs are self-contained and stateless. Once issued, the server can't "cancel" them. Even if you log out, the access token technically still works until it expires.

**The Solution**: When a user logs out, we add their token's `jti` to a Redis blacklist. Every time a protected endpoint is accessed, we check Redis:

```python
# app/services/session_service.py
async def blacklist_token(self, jti: str, expires_delta):
    seconds_remaining = int(expires_delta.total_seconds())
    if seconds_remaining > 0:
        await self.redis.setex(
            f"blacklist:{jti}",    # Key
            seconds_remaining,     # TTL = remaining lifetime of the token
            "1"                    # Value (just needs to exist, "1" is a placeholder)
        )
```

```python
# app/api/deps.py - in get_current_user:
jti = payload.get("jti")
if jti:
    exists = await redis.exists(f"blacklist:{jti}")
    if exists:
        raise HTTPException(401, "Token has been revoked")
```

### Why TTL = Token's Remaining Lifetime?

If the access token expires in 300 seconds, we set the blacklist entry to expire in 300 seconds too. After the token expires naturally, the blacklist entry is no longer needed (expired tokens are already rejected by JWT signature verification). No cleanup needed!

```
Token expires at:  T + 300s
Redis key set at:  T + 0s with TTL=300s
Redis key expires: T + 300s  ← Same time! Perfect cleanup.
```

---

## Email Cooldown with Redis (Phase 4)

To prevent email spam (someone hitting "resend verification email" 100 times):

```python
# After sending a verification email:
await redis.setex(f"email_cooldown:{user_id}", 60, "1")
# User can't request another email for 60 seconds

# Before sending:
if await redis.exists(f"email_cooldown:{user_id}"):
    raise HTTPException(429, "Please wait before requesting another email")
```

The key auto-deletes after 60 seconds. The user can then request again.

---

## OTP Storage with Redis (Phase 4)

When a user requests email verification, we generate a 6-digit OTP and store it in Redis:

```python
# Store OTP:
await redis.setex(f"verify:{user_id}", 600, hashed_otp)
# Key: "verify:user-uuid"
# Value: bcrypt hash of OTP
# TTL: 600 seconds = 10 minutes

# Verify OTP:
stored_hash = await redis.get(f"verify:{user_id}")
if not stored_hash:
    raise HTTPException(400, "OTP expired or not found")
if not verify_password(otp_entered, stored_hash):
    raise HTTPException(400, "Invalid OTP")
# If correct, delete the OTP:
await redis.delete(f"verify:{user_id}")
```

Notice we hash the OTP too! If Redis is compromised, the attacker gets hashes, not real OTPs.

---

## Rate Limiting with Redis (Phase 6)

The sliding window rate limiter:

```python
key = f"ratelimit:{ip_address}:{endpoint}"

# Increment counter:
count = await redis.incr(key)    # Returns new count (creates key if doesn't exist)

# Set TTL only on first request:
if count == 1:
    await redis.expire(key, 60)  # Window = 60 seconds

if count > limit:
    raise HTTPException(429, "Too many requests")
```

How it works:
1. First request: key created, count=1, TTL=60s
2. Requests 2-5: count incremented (2, 3, 4, 5)
3. Request 6: count=6, exceeds limit → 429
4. After 60 seconds: key expires, count resets
5. New requests start fresh

---

## Celery Broker (Phase 4)

Redis also acts as the **message broker** for Celery:

```python
# .env:
CELERY_BROKER_URL=redis://redis:6379/1   # Database 1
CELERY_RESULT_BACKEND=redis://redis:6379/2  # Database 2
```

Redis has 16 logical databases (0-15). We use:
- DB 0: Application data (blacklist, OTPs, cooldowns)
- DB 1: Celery task queue (pending email jobs)
- DB 2: Celery results (completed task status)

Separating them keeps unrelated data organized.

---

## Our Redis Setup

```python
# app/redis.py
import redis.asyncio as redis
from app.config import settings

redis_client = redis.from_url(
    settings.REDIS_URL,          # "redis://redis:6379/0"
    decode_responses=True         # Return strings, not bytes
)

async def get_redis():
    return redis_client
```

`redis_client` is created once at module level and reused. This is a **connection pool** — Redis maintains multiple connections and reuses them efficiently.

### `decode_responses=True`

Redis stores bytes internally. Without this flag:
```python
value = await redis.get("key")  # Returns: b"some_value" (bytes)
```

With `decode_responses=True`:
```python
value = await redis.get("key")  # Returns: "some_value" (string)
```

Much cleaner to work with strings.

---

## Key Naming Convention

We use structured key names to organize Redis keys:

```
blacklist:{jti}           → Token blacklist entries
verify:{user_id}          → Email verification OTPs
reset:{user_id}           → Password reset tokens  
email_cooldown:{user_id}  → Email spam prevention
ratelimit:{ip}:{endpoint} → Rate limiting counters
```

The colon is just a convention (Redis doesn't care about it), but it helps humans understand what each key is for and makes it possible to find related keys with pattern matching:

```python
# Find all blacklist entries:
keys = await redis.keys("blacklist:*")
```

---

## Redis in Our docker-compose.yml

```yaml
redis:
  image: redis:7-alpine    # Alpine = tiny Linux image (less than 10MB)
  ports:
    - "6380:6379"          # 6380 on host (to avoid conflicts), 6379 inside container
  # No password in dev — in production, add:
  # command: redis-server --requirepass yourpassword
```

---

## Summary

- **Redis**: In-memory key-value store — 50-100x faster than PostgreSQL for simple lookups
- **TTL (Time To Live)**: Auto-expiry on keys — set it and forget it; Redis deletes the key
- **Token blacklist**: Store `blacklist:{jti}` with TTL = token's remaining lifetime; check on every request
- **Email cooldown**: `email_cooldown:{user_id}` with 60s TTL; prevent spam
- **OTP storage**: `verify:{user_id}` with 10min TTL; store hashed OTP
- **Rate limiting**: Increment counter per IP per endpoint with 60s TTL window
- **Celery broker**: Redis databases 1 & 2 handle background task queuing
- **`decode_responses=True`**: Get strings back instead of bytes
- **Connection pool**: `redis_client` is one shared pool, not a new connection per request
