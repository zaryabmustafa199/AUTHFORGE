# Lesson 14: FastAPI Dependency Injection

---

## What is Dependency Injection?

**Dependency Injection (DI)** is a design pattern where a piece of code doesn't create the things it needs — instead, those things are "injected" from outside.

**Without DI** (bad pattern):
```python
@router.post("/signup")
async def signup(user_in: UserCreate):
    # Route creates its own database connection:
    engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(engine) as session:
        # ... do stuff
        pass
    # But we can't test this easily! Can't swap the DB connection!
```

**With DI** (what FastAPI does):
```python
@router.post("/signup")
async def signup(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),     # DB is INJECTED
    redis: Redis = Depends(get_redis)       # Redis is INJECTED
):
    # Function doesn't know HOW it got db and redis
    # It just uses them
    auth_service = AuthService(db, redis)
    ...
```

---

## How `Depends()` Works in FastAPI

`Depends(some_function)` tells FastAPI: "Call `some_function()` and give me its return value as this parameter."

```python
# The dependency function:
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session           # Give the session to whoever needs it
        # AFTER the route finishes:
        # Session is automatically closed (AsyncSession's context manager)

# The route uses it:
@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db)):
    # db is a ready-to-use AsyncSession
    # FastAPI called get_db() automatically and injected the result
```

FastAPI handles the entire lifecycle:
1. Before the route: Call `get_db()`, get a session
2. During the route: Route uses the session
3. After the route: Close the session (`async with` does this automatically)

---

## All Dependencies in AuthForge

### `get_db()` — Database Session

```python
# app/api/deps.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
```

Every route that touches the database gets a fresh `AsyncSession`. SQLAlchemy manages a connection pool — `async_session_maker()` doesn't create a new DB connection each time; it grabs one from the pool.

**`yield` vs `return`**:
- `return session` would close the session before the route code runs
- `yield session` pauses here, lets the route run, then resumes (allowing cleanup)

This is called a **generator function** and it's how FastAPI does cleanup after route completion.

### `get_redis()` — Redis Client

```python
# app/redis.py
async def get_redis():
    return redis_client  # Same shared client every time
```

Unlike `get_db()`, `get_redis()` returns the same shared client. Redis connections are cheap and the `redis.asyncio` client handles connection pooling internally.

### `get_current_user()` — Authentication

```python
# app/api/deps.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),   # Extract token from Authorization header
    db: AsyncSession = Depends(get_db),    # Dependencies can depend on other dependencies!
    redis: Redis = Depends(get_redis)
) -> User:
    # 1. Decode and validate JWT
    payload = TokenService.decode_token(token)
    if payload is None:
        raise HTTPException(401, "Could not validate credentials")
    
    # 2. Check token type
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    
    # 3. Check Redis blacklist
    jti = payload.get("jti")
    if jti and await redis.exists(f"blacklist:{jti}"):
        raise HTTPException(401, "Token has been revoked")
    
    # 4. Load user from database
    user_id = payload.get("sub")
    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(401, "User not found")
    
    # 5. Check if user is active
    if not user.is_active:
        raise HTTPException(400, "Inactive user")
    
    return user
```

This is the gatekeeper. ANY route that has `current_user: User = Depends(get_current_user)` is automatically protected.

---

## OAuth2PasswordBearer

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
```

`OAuth2PasswordBearer` is FastAPI's built-in utility that:
1. Looks for the `Authorization` header in the request
2. Checks if it's in the format `Bearer <token>`
3. Extracts and returns the token string

```
Request headers:
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

oauth2_scheme extracts:
"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

If the header is missing or malformed, FastAPI automatically returns `401 Unauthorized`.

The `tokenUrl="api/v1/auth/login"` tells Swagger UI where the login endpoint is, so the "Authorize" button works.

---

## Dependencies Can Depend On Dependencies

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),    # get_db is itself a dependency!
    redis: Redis = Depends(get_redis)
) -> User:
    ...

@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user)  # get_current_user uses 3 deps!
):
    ...
```

FastAPI resolves this **dependency graph** automatically:
1. Route needs `current_user` → call `get_current_user`
2. `get_current_user` needs `token` → call `oauth2_scheme` (extracts from header)
3. `get_current_user` needs `db` → call `get_db` (creates session)
4. `get_current_user` needs `redis` → call `get_redis` (returns client)
5. Now call `get_current_user` with all three
6. Now call the route function with the user

FastAPI also **deduplicates**: if two dependencies both need `get_db`, FastAPI calls `get_db` only once and reuses the result.

---

## The `require_role()` Dependency (Phase 5 Preview)

```python
# app/api/deps.py (Phase 5 addition)
def require_role(allowed_roles: list[str]):
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role.name not in allowed_roles:
            raise HTTPException(403, "Insufficient permissions")
        return current_user
    return Depends(dependency)

# Usage:
@router.get("/admin/users")
async def list_all_users(
    current_user: User = require_role(["admin"])  # Only admins can access
):
    ...
```

`require_role()` is a **dependency factory** — it returns a dependency customized with specific roles. A non-admin calling this endpoint gets a `403 Forbidden`.

---

## Benefits of Dependency Injection

1. **Testability**: In tests, you can swap `get_db` with a test database:
```python
app.dependency_overrides[get_db] = get_test_db  # Override for tests!
```

2. **Reusability**: Define `get_current_user` once, use it in 20 routes

3. **Separation of concerns**: Routes don't know HOW to create a DB session

4. **Automatic lifecycle management**: Sessions are opened before and closed after routes automatically

5. **Composability**: Dependencies can chain together (like `get_current_user` using `get_db`)

---

## Summary

- **Dependency Injection**: Code receives what it needs from outside rather than creating it
- **`Depends(fn)`**: "Call `fn()` and give me its return value as this parameter"
- **`get_db()`**: Creates an `AsyncSession`, yields it to the route, closes it after
- **`get_redis()`**: Returns the shared Redis client
- **`get_current_user()`**: The authentication gatekeeper — validates JWT, checks blacklist, loads user
- **`OAuth2PasswordBearer`**: Extracts the Bearer token from the Authorization header
- **Dependency chaining**: Dependencies can use other dependencies; FastAPI resolves the graph
- **`dependency_overrides`**: In tests, swap real dependencies with test versions (crucial for testing)
- **`require_role()`**: A factory that creates a dependency for role-based access control
