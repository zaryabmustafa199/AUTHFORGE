# Lesson 22: Automated Testing with pytest

---

## Why Test?

Without tests, every code change is a gamble. You change one function and accidentally break three others. Tests are your **safety net** — they tell you immediately if something broke.

For a portfolio project, tests also demonstrate:
- You understand edge cases
- You write maintainable code
- You think about reliability, not just happy paths

---

## The Test Stack

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner — discovers and runs tests |
| `pytest-asyncio` | Enables `async def test_...()` functions |
| `httpx` | Async HTTP client for making API requests in tests |
| `ASGITransport` | Connects httpx to FastAPI without starting a real server |

### Why httpx Instead of requests?

- `requests` is synchronous — it can't work with async FastAPI
- `httpx` supports async and has `ASGITransport` which lets us test FastAPI without starting a real HTTP server
- Tests run in-process (faster, no port conflicts)

---

## Key Concepts

### 1. Fixtures (`conftest.py`)

Fixtures are reusable setup functions that pytest injects into your tests automatically.

```python
@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac   # ← "yield" means: give this to the test, then clean up after
```

Now any test can receive a `client`:

```python
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
```

### 2. Dependency Overrides

In production, `get_db()` returns a database session connected to the real database. In tests, we override it:

```python
app.dependency_overrides[get_db] = _test_db      # Use test database
app.dependency_overrides[get_redis] = _test_redis  # Use test Redis
```

This is FastAPI's built-in mechanism for swapping dependencies during tests. The override map is cleared after each test to prevent leakage.

### 3. Data Isolation

Each test starts with a clean database:

```python
@pytest_asyncio.fixture(autouse=True)
async def clean_data(test_engine, ...):
    async with test_engine.begin() as conn:
        await conn.execute(text(
            "TRUNCATE TABLE audit_logs, sessions, users, roles "
            "RESTART IDENTITY CASCADE"
        ))
    # Re-seed roles
    ...
```

`TRUNCATE ... RESTART IDENTITY CASCADE` is PostgreSQL's fast way to delete all data from multiple tables at once, reset auto-increment counters, and cascade to foreign key relationships.

### 4. Event Loop Management

The biggest challenge with async testing is **event loops**. Key rule: everything async (database engines, Redis clients) must be created inside the test's event loop, not at module import time.

```python
# BAD — created at import time, wrong event loop:
engine = create_async_engine(...)  # Module level

# GOOD — created inside a fixture, correct event loop:
@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(...)
    yield engine
    await engine.dispose()
```

---

## Test Patterns

### Pattern 1: Happy Path

```python
async def test_signup_success(client):
    response = await client.post("/api/v1/auth/signup", json={
        "email": "new@test.com",
        "password": "ValidPass123!",
    })
    assert response.status_code == 201
    assert response.json()["user"]["email"] == "new@test.com"
```

### Pattern 2: Validation Errors

```python
async def test_signup_weak_password(client):
    response = await client.post("/api/v1/auth/signup", json={
        "email": "weak@test.com",
        "password": "short",  # Less than 8 chars
    })
    assert response.status_code == 422  # Pydantic validation error
```

### Pattern 3: Authorization

```python
async def test_admin_only(client, auth_headers):
    headers, _ = auth_headers  # Regular user
    response = await client.get("/api/v1/users/admin/users", headers=headers)
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]
```

### Pattern 4: State Changes

```python
async def test_logout_invalidates_token(client):
    # Login
    login_resp = await client.post("/api/v1/auth/login", data={...})
    tokens = login_resp.json()
    
    # Logout
    await client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}, ...)
    
    # Try to use revoked token — should fail
    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_resp.status_code == 401
```

---

## Our Test Coverage

### Auth Tests (11 tests)
- ✅ Signup: success, duplicate email, weak password, invalid email
- ✅ Login: success, wrong password, nonexistent user
- ✅ Token refresh: rotation works, invalid token rejected
- ✅ Logout: token blacklisted, can't reuse
- ✅ Health check

### RBAC Tests (8 tests)
- ✅ Profile: view own, update own, unauthenticated rejected
- ✅ Admin: list users, change role, can't change own role
- ✅ Permissions: regular user gets 403 on admin routes
- ✅ Audit logs: admin can view

---

## Running Tests

```bash
# All tests
docker-compose exec app pytest -v

# Specific file
docker-compose exec app pytest app/tests/test_auth.py -v

# Specific test
docker-compose exec app pytest app/tests/test_auth.py::test_login_success -v

# With coverage report (if pytest-cov installed)
docker-compose exec app pytest --cov=app -v
```
