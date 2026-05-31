# Lesson 13: Sessions & Token Rotation

---

## What is a Session in This Context?

A **session** represents one logged-in device. Every time you log in (whether from your phone, laptop, or another browser), a new session record is created in the database.

```
User: alice@example.com
Sessions:
├── Session 1: iPhone 14 Pro, logged in 2 days ago, IP: 192.168.1.5
├── Session 2: MacBook Pro, logged in 1 hour ago, IP: 10.0.0.1
└── Session 3: Chrome on Windows, logged in 5 minutes ago, IP: 203.10.5.22
```

This is the "Active Sessions" feature you see on Google, GitHub, and Netflix — where you can see all your logged-in devices and remotely log out any of them.

---

## What's Stored in a Session Row?

```python
class Session(Base):
    id               # UUID — unique per session
    user_id          # Which user owns this session
    refresh_token_hash   # Bcrypt hash of the refresh token (NOT the raw token)
    device_info      # "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0...)"
    ip_address       # "192.168.1.5"
    is_revoked       # False = active, True = logged out
    created_at       # When the login happened
    expires_at       # When this session should die (7 days from creation)
```

The session acts as a **server-side record of a refresh token**. When someone uses a refresh token, we check:
1. Is this token valid? (JWT signature)
2. Does a matching, non-revoked session exist in DB? (extra security layer)

---

## Why Store Sessions at All? JWT Is "Stateless"

The whole point of JWT is that the server doesn't need to store anything. So why do we have a sessions table?

**The Problem with Pure Stateless JWT**:

You cannot log out a user. If Alice's refresh token is stolen, the attacker can keep refreshing for 7 days, and there's NOTHING you can do. You can't "cancel" a JWT — the server doesn't track them.

**The Solution**: Store sessions. When you want to log out a device:
1. Mark the session as `is_revoked=True` in the database
2. Blacklist the token's JTI in Redis

Now the stolen refresh token is useless — the session is revoked.

**The tradeoff**: We give up a tiny bit of "stateless purity" for a huge security gain.

---

## Session Lifecycle

```
LOGIN:
user logs in with email/password
    → tokens created
    → session row created in DB:
       {refresh_token_hash: hash(token), is_revoked: False, expires_at: now+7d}
    → access_token + refresh_token returned to client

NORMAL API CALL:
client sends: Authorization: Bearer <access_token>
    → get_current_user: decode JWT, check blacklist, load user
    → NO session lookup needed for regular API calls (truly stateless)

ACCESS TOKEN EXPIRES (after 15 min):
client sends: POST /auth/refresh {refresh_token}
    → decode refresh token: valid JWT? ✓ type=refresh? ✓
    → check Redis blacklist: jti not blacklisted? ✓
    → find session: loop through user's active sessions, bcrypt.verify(token, hash)? ✓
    → blacklist old token's jti in Redis
    → revoke old session row (is_revoked=True)
    → create NEW access_token + NEW refresh_token
    → create NEW session row in DB
    → return new tokens

LOGOUT:
client sends: POST /auth/logout {refresh_token}
    + Authorization: Bearer <access_token>
    → blacklist access_token's jti in Redis (with remaining lifetime as TTL)
    → blacklist refresh_token's jti in Redis
    → find matching session → mark is_revoked=True
    → return 204 No Content
```

---

## Token Rotation: What It Is and Why

**Token rotation** means: every time you use a refresh token to get a new access token, the old refresh token is destroyed and a brand new one is issued.

### Without Rotation (Vulnerable):
```
1. Alice logs in → gets refresh_token_A (valid 7 days)
2. Attacker steals refresh_token_A
3. Alice logs out → session marked revoked
4. Attacker uses refresh_token_A → server: session revoked → REJECTED ✓

But what if:
3. Attacker uses refresh_token_A BEFORE Alice logs out
4. Attacker gets new tokens and stays logged in forever
5. Alice can't see the attacker's session (they have a new one)
```

### With Rotation (What We Built):
```
1. Alice logs in → gets refresh_token_A + session_A
2. Alice uses refresh_token_A → gets refresh_token_B + session_B
   (refresh_token_A is blacklisted, session_A is revoked)
3. If attacker had stolen refresh_token_A and tries to use it later → REJECTED
   (already blacklisted/revoked)
4. If attacker uses it BEFORE Alice does → attacker gets refresh_token_B
   BUT when Alice tries to use refresh_token_A → it's already used!
   → Server can detect this and invalidate ALL sessions for Alice (theft detection)
```

Token rotation provides **theft detection**: if a token is used twice, someone stole it.

---

## The "Immediate Revocation" Question

You asked: "I revoked a session but `/me` still works. Why?"

**Answer**: Access tokens are checked against the JWT signature and expiry, but NOT against the sessions table.

```
Session revoked (DB: is_revoked=True)
    ↓
Attacker uses access_token
    ↓
get_current_user:
1. JWT signature valid? ✓
2. Not expired? ✓ (15 min token, just issued)
3. Not in Redis blacklist? ✓ (you didn't blacklist the ACCESS token, only the session)
4. User exists in DB? ✓
→ ACCESS GRANTED (even though session is revoked!)
```

**Why this is acceptable** in most systems: Access tokens expire in 15 minutes. For most use cases, a 15-minute window is acceptable.

**If you want truly immediate revocation** (like banking apps), you'd:
1. Include the `session_id` in the access token JWT
2. In `get_current_user`, do a DB lookup: `SELECT is_revoked FROM sessions WHERE id = session_id`
3. If `is_revoked=True` → reject

Trade-off: Every API call now hits the database. Less "stateless" but fully immediate.

---

## Session Repository

```python
# app/repositories/session_repo.py
class SessionRepository:
    async def create(self, user_id, refresh_token_hash, expires_at, ...):
        db_session = Session(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,  # Already hashed before calling this
            expires_at=expires_at,
            ...
        )
        self.session.add(db_session)
        await self.session.commit()
        return db_session

    async def get_active_sessions_for_user(self, user_id) -> List[Session]:
        # Return only non-revoked sessions
        result = await self.session.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.is_revoked == False   # Only active sessions
            )
        )
        return list(result.scalars().all())

    async def revoke(self, session: Session):
        session.is_revoked = True
        await self.session.commit()
        # The session object is "attached" to the SQLAlchemy session
        # Modifying it and committing updates the DB row
```

---

## `GET /sessions` — The "Active Devices" Endpoint

```python
# app/api/v1/sessions.py
@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user)
):
    session_service = SessionService(db, redis)
    return await session_service.session_repo.get_active_sessions_for_user(current_user.id)
```

Returns all non-revoked sessions for the current user. This is like Google's "Your devices" page.

## `DELETE /sessions/{session_id}` — Remote Logout

```python
@router.delete("/{session_id}", status_code=204)
async def revoke_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user)
):
    await session_service.revoke_session(session_id, current_user.id)
```

Security check: `revoke_session` verifies `session.user_id == current_user.id`. You can only revoke YOUR OWN sessions, not other people's.

---

## Why `verify_password` for Refresh Token Matching?

```python
# In refresh_token and logout methods:
for sess in active_sessions:
    if verify_password(refresh_token, sess.refresh_token_hash):
        current_session = sess
        break
```

In the DB we only have `refresh_token_hash`. We can't look up "session where token = X" directly because bcrypt is non-deterministic (same input, different salt, different hash each time).

So we:
1. Get all active sessions for this user
2. For each session, call `bcrypt.verify(incoming_token, stored_hash)`
3. When it matches, we've found the correct session

Performance note: A user typically has 2-5 active sessions. Each bcrypt.verify takes ~100ms. So worst case: 500ms to find the session. Acceptable for a refresh operation (not done often).

---

## Summary

- **Session**: A DB record representing one logged-in device; stores hashed refresh token, device info, IP
- **Why sessions with JWT**: JWTs are stateless, but sessions enable logout, device management, and theft detection
- **Token rotation**: Old refresh token is destroyed and replaced on every use; prevents reuse of stolen tokens
- **`is_revoked`**: Boolean flag; `True` = this device has been logged out
- **Redis blacklist**: For immediate invalidation of tokens during logout
- **`revoke_session`**: Users can only revoke their own sessions (security check: `session.user_id == current_user.id`)
- **"Immediate revocation" tradeoff**: Session revocation doesn't instantly stop access tokens; 15min window is acceptable; fix by checking session DB in every request (but adds DB hit)
- **`verify_password` for token matching**: We can't look up by hash directly; iterate and verify each active session
