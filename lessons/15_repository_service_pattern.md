# Lesson 15: Repository Pattern & Service Layer Architecture

---

## The Problem: Mixing Concerns

Beginners often write code like this:

```python
@router.post("/signup")
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Route is doing EVERYTHING:
    
    # 1. Check if user exists (SQL query in the route!)
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(400, "Email taken")
    
    # 2. Hash password (security logic in the route!)
    hashed = get_password_hash(user_in.password)
    
    # 3. Create user (SQL in the route!)
    user = User(email=user_in.email, hashed_password=hashed)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return {"user": user}
```

This works for small apps. But as the app grows:
- Your route becomes 200 lines long
- Can't reuse the "check if email taken" logic elsewhere
- Can't test business logic without making HTTP requests
- Can't swap PostgreSQL for another database without touching every route

---

## The Three-Layer Architecture

AuthForge separates code into three layers:

```
┌─────────────────────────────────────────────────────────┐
│                  ROUTE (API Layer)                       │
│  • Receives HTTP request                                 │
│  • Validates input (Pydantic)                           │
│  • Calls the service                                     │
│  • Returns HTTP response                                 │
│  • NO business logic, NO SQL                            │
├─────────────────────────────────────────────────────────┤
│                SERVICE LAYER                            │
│  • Business logic ("should this user be allowed?")      │
│  • Orchestrates multiple repository calls               │
│  • Raises HTTP exceptions with meaningful messages       │
│  • NO raw SQL queries                                   │
├─────────────────────────────────────────────────────────┤
│               REPOSITORY LAYER                          │
│  • ONLY database queries                               │
│  • No business logic                                    │
│  • No HTTP concerns                                     │
│  • Easy to swap database (change only here)             │
└─────────────────────────────────────────────────────────┘
```

---

## Repositories in AuthForge

### `user_repo.py`

```python
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalars().first()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalars().first()

    async def create(self, user_in: UserCreate) -> User:
        db_user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name
        )
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user
```

**Rules**:
- Only SQL/ORM queries in here
- No `if` conditions based on business rules
- No `HTTPException` — raises `None` or raises database errors
- Receives schema objects (`UserCreate`) and returns model objects (`User`)

### `session_repo.py`

```python
class SessionRepository:
    async def create(self, user_id, refresh_token_hash, expires_at, ...):
        # Just creates the row
        
    async def get_active_sessions_for_user(self, user_id) -> List[Session]:
        # Just queries: WHERE user_id=? AND is_revoked=False
        
    async def get_by_id(self, session_id) -> Optional[Session]:
        # Just queries: WHERE id=?
        
    async def revoke(self, session: Session):
        # Just sets is_revoked=True and commits
```

Notice: `session_repo` doesn't know WHY it's revoking a session. It just does it. The WHY is the service's job.

---

## Services in AuthForge

### `auth_service.py`

```python
class AuthService:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.user_repo = UserRepository(session)
        self.token_service = TokenService()
        self.session_service = SessionService(session, redis)
    
    async def signup(self, user_in: UserCreate) -> User:
        # BUSINESS LOGIC:
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:  # ← Business rule: no duplicate emails
            raise HTTPException(400, "Email already registered")
        
        user = await self.user_repo.create(user_in)
        # Phase 4 addition: queue verification email
        # send_verification_email.delay(user.id, user.email)
        return user
    
    async def login(self, email, password, device_info, ip_address) -> dict:
        # Multiple concerns coordinated:
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise HTTPException(401, "Incorrect email or password")  # ← Don't reveal which
        
        if not verify_password(password, user.hashed_password):
            raise HTTPException(401, "Incorrect email or password")  # ← Same message for security
        
        access_token = self.token_service.create_access_token(user.id)
        refresh_token_data = self.token_service.create_refresh_token(user.id)
        
        await self.session_service.create_session(...)  # ← Coordinates with session service
        
        return {"access_token": ..., "refresh_token": ..., "token_type": "bearer"}
```

The service **orchestrates**: it calls multiple repos/services and contains the business rules.

### `session_service.py`

```python
class SessionService:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.session_repo = SessionRepository(session)
        self.redis = redis
    
    async def create_session(self, user_id, refresh_token, expires_at, ...):
        # Business logic: hash the token before storing
        token_hash = get_password_hash(refresh_token)
        return await self.session_repo.create(user_id, token_hash, expires_at, ...)
    
    async def blacklist_token(self, jti: str, expires_delta):
        # Business logic: what TTL to use, how to format the key
        seconds = int(expires_delta.total_seconds())
        if seconds > 0:
            await self.redis.setex(f"blacklist:{jti}", seconds, "1")
    
    async def is_blacklisted(self, jti: str) -> bool:
        return await self.redis.exists(f"blacklist:{jti}") > 0
    
    async def revoke_session(self, session_id: UUID, current_user_id: UUID):
        # Business logic: users can only revoke THEIR OWN sessions
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != current_user_id:
            raise HTTPException(404, "Session not found")  # ← Business rule
        await self.session_repo.revoke(session)
```

### `token_service.py`

```python
class TokenService:
    # Pure utility — no DB, no Redis
    # Just JWT creation and verification
    
    @staticmethod
    def create_access_token(user_id: str) -> str: ...
    
    @staticmethod
    def create_refresh_token(user_id: str) -> dict: ...
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]: ...
```

`TokenService` is the simplest — pure functions with no external dependencies. Easy to test.

---

## How It All Flows for Signup

```
POST /api/v1/auth/signup
    │
    ▼ auth.py (ROUTE)
    │  1. Pydantic validates UserCreate
    │  2. Injects db, redis via Depends()
    │  3. Creates AuthService(db, redis)
    │  4. Calls auth_service.signup(user_in)
    │
    ▼ auth_service.py (SERVICE)
    │  1. Calls user_repo.get_by_email(email) → None (user doesn't exist)
    │  2. Calls user_repo.create(user_in) → User object
    │  3. Returns User
    │
    ▼ user_repo.py (REPOSITORY)
    │  1. Calls get_password_hash(password)
    │  2. Creates User model object
    │  3. session.add(user), commit(), refresh()
    │  4. Returns User from DB (with generated id, timestamps)
    │
    ▲ (result bubbles back up)
    │
    ▼ auth.py (ROUTE)
    │  5. Returns {"user": user} (FastAPI serializes via SignupResponse)
```

---

## Why Not Just Put Everything in the Service?

Some code belongs in the repository, not the service:

| Belongs in Repository | Belongs in Service |
|----------------------|-------------------|
| SQL queries | Business rules |
| Pagination logic | Error messages |
| Index/join optimization | Orchestration of multiple repos |
| DB-specific features | Authentication checks |

If you put SQL in the service, you can't swap databases without touching business logic.

---

## Benefits of This Architecture

1. **Testability**: Test `auth_service.py` by mocking `user_repo`. No real database needed.
2. **Replaceability**: Want to switch from PostgreSQL to MongoDB? Only change `user_repo.py`.
3. **Readability**: Each file has one clear responsibility.
4. **Reusability**: `user_repo.get_by_email()` is used by auth, profile updates, password reset.
5. **Team collaboration**: One developer works on routes, another on services, another on repos.

---

## Summary

- **Repository**: Only SQL/ORM queries. No business logic. No HTTP exceptions.
- **Service**: Business logic and orchestration. Uses repositories. Raises HTTP exceptions.
- **Route**: HTTP concerns only. Validates input, calls service, returns response.
- **3 layers** = 3 reasons to change = clean separation of concerns
- `auth_service` uses `user_repo`, `token_service`, and `session_service` — it orchestrates
- `session_service` uses `session_repo` and `redis` — a smaller scope
- `token_service` = pure JWT functions, no external dependencies
