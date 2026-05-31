# Lesson 11: JWT Tokens & Authentication

---

## The Problem: How Does the Server Know It's You?

HTTP is **stateless** — every request is independent. The server doesn't remember you. So how does an API know that request #1,247 is from Alice and not Bob?

### Old Approach: Sessions (Cookie-Based)

```
1. Alice logs in
2. Server creates a "session" with ID "abc123" and stores it in memory/DB
3. Server sends cookie: session_id=abc123
4. Alice's browser sends that cookie on every request
5. Server looks up "abc123" in its session store
6. Finds Alice's data → knows it's Alice
```

**Problems**:
- Server must store session data (doesn't scale well with millions of users)
- Cookie-based (doesn't work well for mobile apps or other APIs)

### Modern Approach: JWT (Stateless)

```
1. Alice logs in
2. Server creates a signed token containing Alice's user ID and expiry
3. Server sends the token to Alice (no storage on server!)
4. Alice sends that token in every request header
5. Server decodes and verifies the token's signature
6. Token contains Alice's ID → server knows it's Alice (no DB lookup needed)
```

**Benefits**:
- Server doesn't store anything — scales to millions of users easily
- Works for any client (browser, mobile app, another API)
- Self-contained — all info is in the token

---

## What is a JWT?

**JWT** (JSON Web Token) has 3 base64-encoded parts separated by dots:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLXV1aWQiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjE1MDAwMDAwfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
│───────────────────────────────────────│───────────────────────────────────────────────────│────────────────────────────────────────────│
              HEADER                                         PAYLOAD                                     SIGNATURE
```

### Part 1: Header

Decoded:
```json
{
    "alg": "HS256",   // Algorithm used to create the signature
    "typ": "JWT"      // Type of token
}
```

### Part 2: Payload (Claims)

Decoded:
```json
{
    "sub": "550e8400-e29b-41d4-a716-446655440000",  // "subject" = user ID
    "type": "access",    // Access or refresh token
    "exp": 1715000000,   // Expiry timestamp (Unix timestamp)
    "jti": "unique-uuid" // JWT ID — unique per token (for blacklisting)
}
```

`sub`, `exp`, `jti` are **standard JWT claims** (defined in the JWT RFC). `type` is our custom claim.

### Part 3: Signature

```
HMAC_SHA256(
    base64url(header) + "." + base64url(payload),
    SECRET_KEY
)
```

The signature is a cryptographic fingerprint of the header + payload. If ANYONE changes even one character in the payload, the signature becomes invalid.

---

## How Signing Works

```python
# TokenService creates a token:
SECRET_KEY = "d87f2a9b3c1e5f4a8d2b7c9e..."  # From .env

payload = {
    "sub": "user-uuid",
    "type": "access",
    "exp": datetime(2024, 1, 2, ...),  # 15 minutes from now
    "jti": "random-uuid"
}

# jwt.encode signs the payload with our secret:
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
# Returns: "eyJhbGci...header.payload.signature"
```

**Verification**:
```python
# When a request arrives with token:
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
# jwt.decode:
# 1. Splits the token into header + payload + signature
# 2. Recalculates: expected_sig = HMAC(header+payload, SECRET_KEY)
# 3. Compares expected_sig with actual signature in token
# 4. If they match → payload is valid and untampered
# 5. Also checks: has the "exp" time passed? If yes → raises ExpiredSignatureError
```

---

## Access Token vs. Refresh Token

Both are JWTs. The difference is in their purpose and lifespan.

### Access Token

```python
# Created in token_service.py:
expire = datetime.now(UTC) + timedelta(minutes=15)  # 15 MINUTES
jti = str(uuid4())
payload = {
    "sub": user_id,
    "type": "access",
    "exp": expire,
    "jti": jti
}
```

- **Short-lived**: 15 minutes
- **Used for**: Every API call (Authorization header)
- **If stolen**: Only valid for 15 minutes

### Refresh Token

```python
# Created in token_service.py:
expire = datetime.now(UTC) + timedelta(days=7)  # 7 DAYS
jti = str(uuid4())  # Unique ID for this token (for blacklisting)
payload = {
    "sub": user_id,
    "type": "refresh",
    "exp": expire,
    "jti": jti
}
```

- **Long-lived**: 7 days
- **Used for**: Only `/auth/refresh` endpoint
- **If stolen**: Can get new tokens for 7 days (mitigated by rotation, see Lesson 13)
- **Stored in DB** (as hash) in sessions table
- **Only ONE purpose**: Getting new access tokens

### The Pair Strategy

```
Login → Get access_token (15min) + refresh_token (7days)

Normal API calls:
Authorization: Bearer <access_token>

When access_token expires:
POST /auth/refresh
Body: refresh_token
→ Get new access_token (fresh 15min) + new refresh_token (fresh 7days)
```

---

## Why Check `type` in the Token?

```python
# app/api/deps.py
if payload.get("type") != "access":
    raise HTTPException(401, "Invalid token type")
```

Without this check, someone could use a refresh token as an access token:
- Refresh tokens last 7 days
- An attacker with a stolen refresh token could use it to call `/users/me` for 7 days instead of 15 minutes

By checking `type`, we ensure:
- `access` tokens → only for API calls
- `refresh` tokens → only for `/auth/refresh`

---

## Why Every Token Has a Unique `jti`?

`jti` (JWT ID) is a unique identifier for each token. Without it, you can't blacklist individual tokens.

```python
# On logout, we blacklist the jti:
await redis.setex(f"blacklist:{jti}", seconds_remaining, "1")

# On every request, we check:
exists = await redis.exists(f"blacklist:{jti}")
if exists: raise HTTPException(401, "Token revoked")
```

If two tokens had the same `jti`, blacklisting one would blacklist both.

---

## The TokenService in AuthForge

```python
# app/services/token_service.py
import jwt
from uuid import uuid4
from app.config import settings

class TokenService:
    @staticmethod
    def create_access_token(user_id: str) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jti = str(uuid4())
        payload = {"sub": str(user_id), "type": "access", "exp": expire, "jti": jti}
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        # ALGORITHM = "HS256" (from config)

    @staticmethod
    def create_refresh_token(user_id: str) -> dict:
        expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        jti = str(uuid4())
        payload = {"sub": str(user_id), "type": "refresh", "exp": expire, "jti": jti}
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return {"token": token, "jti": jti, "exp": expire}
        # Returns dict (not just string) because auth_service needs jti and exp

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except jwt.PyJWTError:
            return None   # Returns None for expired, invalid, or tampered tokens
```

---

## HS256 vs. RS256

| Algorithm | Type | How It Works | When to Use |
|-----------|------|-------------|------------|
| **HS256** | Symmetric | Same secret key for signing AND verifying | Single server (what we use) |
| **RS256** | Asymmetric | Private key signs, public key verifies | Multiple services / microservices |

We use **HS256** because AuthForge is a single server. The secret key signs the token and the same key verifies it.

RS256 would be needed if, say, one service issues tokens and another service (that shouldn't have the private key) needs to verify them.

---

## What Happens if SECRET_KEY Changes?

ALL existing tokens become invalid instantly. Every user gets logged out.

This is actually useful: if you suspect your SECRET_KEY was compromised, you change it and every attacker's stolen token becomes worthless immediately.

---

## Summary

- **JWT** = a signed JSON token that proves who you are without server-side session storage
- **Header**: algorithm used to sign
- **Payload (claims)**: sub (user ID), type, exp (expiry), jti (unique ID)
- **Signature**: cryptographic proof the payload wasn't tampered with
- **Access token**: short-lived (15min), used for every API call
- **Refresh token**: long-lived (7d), used only to get new access tokens
- **`type` claim**: prevents using refresh tokens as access tokens
- **`jti` claim**: unique ID per token, allows individual token blacklisting
- **HS256**: symmetric algorithm — same key signs and verifies (fine for single server)
- **`decode_token` returns None**: if token is expired, invalid, or tampered
