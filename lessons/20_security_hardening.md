# Lesson 20: Security Hardening — Rate Limiting, Brute-Force, Audit Logs

---

## 1. Rate Limiting

### The Problem

Without rate limiting, an attacker can:
- Try thousands of passwords per second on `/login` (brute force)
- Create thousands of fake accounts on `/signup` (spam)
- Trigger thousands of reset emails on `/forgot-password` (email bombing)

### The Solution: Redis Sliding Window Counter

```
Request comes in → Get client IP → Build Redis key → Increment counter → Check limit
```

```python
redis_key = f"ratelimit:login:192.168.1.1"  # prefix:endpoint:IP

current_count = await redis.incr(redis_key)  # Atomic increment (1, 2, 3...)
if current_count == 1:
    await redis.expire(redis_key, 60)        # Set 60-second window on first request

if current_count > 5:                         # Over limit!
    raise HTTPException(status_code=429, detail="Too many requests")
```

### How the Window Works

```
Time 0:00  → Request 1 → count=1, TTL set to 60s
Time 0:10  → Request 2 → count=2
Time 0:20  → Request 3 → count=3
Time 0:30  → Request 4 → count=4
Time 0:40  → Request 5 → count=5
Time 0:50  → Request 6 → count=6 → BLOCKED! (429 Too Many Requests)
Time 1:00  → Key expires → count resets to 0
Time 1:01  → Request 7 → count=1 → Allowed again
```

### Fail-Open Design

```python
except RedisError:
    # Fail open: if Redis is down, don't block requests
    pass
```

Rate limiting is a **nicety** — if Redis is temporarily down, it's better to let some extra requests through than to block ALL users. Compare this to the blacklist check in `get_current_user`, which **fails closed** (blocks all requests) because security is critical there.

### Our Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/signup` | 3 requests | 60 seconds |
| `/login` | 5 requests | 60 seconds |
| `/forgot-password` | 3 requests | 60 seconds |

---

## 2. Brute-Force Account Lockout

Rate limiting protects per-IP. But what if an attacker uses thousands of different IPs (a botnet)?

We add a **per-account** lockout using the email address:

```python
# On failed login:
counter_key = f"failed_login:user@example.com"
count = await redis.incr(counter_key)

if count >= 5:  # 5 failed attempts
    await redis.setex(f"lockout:user@example.com", 900, "1")  # Lock for 15 minutes
    await redis.delete(counter_key)

# On successful login:
await redis.delete(f"failed_login:user@example.com")  # Reset counter
```

### The Flow

```
Attempt 1: Wrong password → count=1 → "Incorrect email or password"
Attempt 2: Wrong password → count=2 → "Incorrect email or password"
Attempt 3: Wrong password → count=3 → "Incorrect email or password"
Attempt 4: Wrong password → count=4 → "Incorrect email or password"
Attempt 5: Wrong password → count=5 → LOCKED! → "Account locked. Try again in 900 seconds"
Attempt 6: Correct password → STILL LOCKED → "Account locked. Try again in 850 seconds"
... wait 15 minutes ...
Attempt 7: Correct password → SUCCESS → counter cleared
```

### Why 423 (Locked) Instead of 429 (Too Many Requests)?

HTTP 423 specifically means "the resource is **locked**" — the account itself is locked, not just rate-limited. This is semantically more accurate than 429.

---

## 3. Audit Logging

### What Is an Audit Log?

An immutable record of every security-sensitive action in the system. Like a security camera for your API.

### What Gets Logged

| Action | When | Extra Data |
|--------|------|-----------|
| `SIGNUP` | New user created | email |
| `LOGIN` | Successful login | device info |
| `LOGIN_FAILED` | Wrong password or user not found | email, reason |
| `LOGOUT` | User logged out | — |
| `EMAIL_VERIFIED` | OTP validated | — |
| `PASSWORD_RESET_REQUESTED` | Reset email sent | — |
| `PASSWORD_RESET_COMPLETED` | Password changed | sessions revoked count |
| `ROLE_CHANGED` | Admin changed a user's role | old_role → new_role, changed_by |
| `ACCOUNT_LOCKED` | Too many failed logins | email, failed_attempts |
| `PROFILE_UPDATED` | User updated their profile | field changes |

### Fire-and-Forget Pattern

```python
async def log(self, action, user_id=None, ip_address=None, metadata_info=None):
    await self.repo.create(action=action, user_id=user_id, ...)
```

The audit service **never raises exceptions**. If writing to the audit log fails (database full, connection error), we log the error but don't break the user's request. The actual action (login, signup, etc.) is more important than recording it.

### Admin Audit Log Viewer

Admins can view the entire audit trail:

```
GET /api/v1/users/admin/audit-logs?page=1&per_page=50&action=LOGIN_FAILED
```

This lets admins:
- See who's trying to brute-force accounts (`LOGIN_FAILED`)
- Track role changes (`ROLE_CHANGED`)
- Monitor signup patterns (`SIGNUP`)
- Investigate security incidents

---

## 4. Security Headers

Every HTTP response includes these headers:

| Header | Value | What It Prevents |
|--------|-------|-----------------|
| `X-Content-Type-Options` | `nosniff` | Browser guessing file types (MIME sniffing attacks) |
| `X-Frame-Options` | `DENY` | Your site being embedded in iframes (clickjacking) |
| `X-XSS-Protection` | `1; mode=block` | Browser-level XSS filtering |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Leaking full URLs when navigating away |

These are set in middleware so they apply to **every single response** automatically.

---

## Summary

| Defense Layer | Protects Against | Mechanism |
|--------------|-----------------|-----------|
| Rate Limiting | API abuse, mass requests | Redis counter per IP + endpoint |
| Brute-Force Lockout | Password guessing, botnets | Redis counter per email address |
| Audit Logging | Incident investigation, compliance | Append-only database records |
| Security Headers | XSS, clickjacking, MIME attacks | HTTP response headers |
