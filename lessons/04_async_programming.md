# Lesson 04: Async Programming (async/await)

---

## The Problem: Waiting is Expensive

Imagine a restaurant with one waiter. A customer orders food. The waiter walks to the kitchen, stands there waiting for the food to be cooked (5 minutes), then brings it back.

During those 5 minutes, that waiter is doing nothing. If 10 customers arrive, they all wait in a queue because the waiter is stuck waiting at the kitchen.

This is how **synchronous (blocking) code** works in programming:

```python
# Synchronous (blocking):
def get_user(user_id):
    user = database.query(User).get(user_id)  # STOPS HERE and waits for DB
    return user                                 # Then continues

def handle_request():
    user = get_user(123)   # Blocks for 50ms while DB responds
    do_something(user)     # Then this runs
```

---

## The Solution: Async (Non-Blocking)

A smarter waiter takes the order, walks to the kitchen, **puts in the order**, then goes back to take other customers' orders. When the kitchen calls "order ready!", the waiter picks it up and delivers it.

This is **asynchronous (non-blocking) code**:

```python
# Asynchronous (non-blocking):
async def get_user(user_id):
    user = await database.execute(...)  # "Submit the query and come back when done"
    return user                          # Continues after DB responds

async def handle_request():
    user = await get_user(123)   # "Start the query, let other things run meanwhile"
    do_something(user)
```

During the `await`, Python can handle thousands of other requests. When the database responds, Python picks up right where it left off.

---

## Key Terms

| Term | Meaning |
|------|---------|
| `async def` | Marks a function as asynchronous. It CAN use `await`. |
| `await` | "Wait for this async operation to complete, but let other things run while waiting." |
| **Coroutine** | What `async def` functions return. Not a regular value — it's a "promise" of a value. |
| **Event Loop** | The scheduler that manages all coroutines — decides which one to run next. |
| **I/O Bound** | Operations that spend time waiting (network, database, file) — benefit from async. |
| **CPU Bound** | Operations that spend time calculating — async doesn't help (use multiprocessing). |

---

## The Golden Rule

```python
# WRONG: calling a sync function from async context
async def get_user():
    return db.execute(query)  # This BLOCKS the entire server!

# RIGHT: using async function
async def get_user():
    return await db.execute(query)  # Non-blocking ✓
```

**You cannot mix sync and async without understanding the consequences.**

If you call a blocking function (like a regular `requests.get()` HTTP call) inside an `async def`, it freezes the entire event loop — all other requests have to wait. This is a common beginner mistake.

---

## Why Does AuthForge Use Async Everywhere?

A web server handles many simultaneous users. If 100 users are all waiting for database responses at the same time:

- **Sync server**: Would need 100 threads/processes (uses GBs of RAM, crashes under load)
- **Async server**: One event loop handles all 100 with minimal memory overhead

FastAPI is built for async. SQLAlchemy 2.0 supports async. Asyncpg (PostgreSQL driver) is async. Redis async client. Everything in AuthForge is async by design.

---

## How It Looks in AuthForge

```python
# app/repositories/user_repo.py
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session  # AsyncSession — not regular Session

    async def get_by_email(self, email: str) -> Optional[User]:
        # 1. Build a query
        stmt = select(User).where(User.email == email)
        
        # 2. Execute it — await releases control to the event loop
        result = await self.session.execute(stmt)
        
        # 3. Extract the first row
        return result.scalars().first()

    async def create(self, user_in: UserCreate) -> User:
        db_user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
        )
        self.session.add(db_user)
        
        # Commit to database — await releases control during network wait
        await self.session.commit()
        
        # Reload from DB to get auto-generated id/timestamps
        await self.session.refresh(db_user)
        return db_user
```

```python
# app/services/auth_service.py
class AuthService:
    async def signup(self, user_in: UserCreate) -> User:
        # Each await is a "checkpoint" where other requests can be handled
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(400, "Email already registered")
        
        user = await self.user_repo.create(user_in)
        return user
```

```python
# app/api/v1/auth.py
@router.post("/signup", response_model=SignupResponse)
async def signup(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    auth_service = AuthService(db, redis)
    user = await auth_service.signup(user_in)
    return {"user": user}
```

Notice that everything is `async def` and every database/redis call uses `await`.

---

## What About asyncpg?

`asyncpg` is the PostgreSQL driver for Python. The regular `psycopg2` driver is synchronous — it was written before async Python existed. `asyncpg` was built from scratch to be fully async.

When we write `DATABASE_URL=postgresql+asyncpg://...`, we're telling SQLAlchemy to use asyncpg under the hood for all database connections.

---

## Redis Async

```python
# app/redis.py
import redis.asyncio as redis  # The async version of the redis library
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# In session_service.py:
async def blacklist_token(self, jti: str, expires_delta):
    seconds_remaining = int(expires_delta.total_seconds())
    await self.redis.setex(f"blacklist:{jti}", seconds_remaining, "1")
    #     ↑
    # Non-blocking Redis call
```

---

## Async in FastAPI Dependencies

```python
# app/api/deps.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session  # Give the session to the route
        # After the route finishes, the session is closed automatically
```

`async with` and `async for` are async versions of `with` and `for`. They work with objects that implement asynchronous context managers.

---

## Summary

- **Synchronous**: Code runs line by line, blocking everything while waiting for I/O
- **Asynchronous**: Code starts an operation and lets others run while waiting
- **async def**: Marks a function as a coroutine (must be awaited by the caller)
- **await**: "Wait for this, but release control to the event loop in the meantime"
- **Why use it**: A web server can handle thousands of concurrent users with minimal resources
- **AuthForge**: Every route, service, repository, and database/redis call is async
- The keywords to look for in our code: `async def`, `await`, `AsyncSession`, `redis.asyncio`
