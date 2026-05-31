# Lesson 03: HTTP, REST APIs & FastAPI

---

## What is HTTP?

**HTTP** (HyperText Transfer Protocol) is the language that browsers and servers use to talk to each other. Every time you visit a website, your browser sends an HTTP **request** and the server sends back an HTTP **response**.

```
Browser / Client                         Server
     │                                     │
     │── GET /api/v1/auth/me ─────────────►│  "Give me my profile"
     │   Header: Authorization: Bearer ... │
     │                                     │  (server validates token, looks up user)
     │◄── 200 OK ──────────────────────────│  "Here's your profile"
     │   Body: {"id": "...", "email": ...} │
```

### HTTP Methods (Verbs)

| Method | Meaning | AuthForge Example |
|--------|---------|-------------------|
| `GET` | Read data | `GET /sessions` — list my sessions |
| `POST` | Create/send data | `POST /signup` — create a new user |
| `PUT` | Replace entire resource | `PUT /users/1` — replace user completely |
| `PATCH` | Update part of a resource | `PATCH /users/me` — update just name |
| `DELETE` | Remove a resource | `DELETE /sessions/{id}` — revoke a session |

### HTTP Status Codes

| Code | Name | When Used |
|------|------|-----------|
| `200` | OK | Request succeeded |
| `201` | Created | New resource was created (signup) |
| `204` | No Content | Success, nothing to return (logout) |
| `400` | Bad Request | Client sent bad data (email already taken) |
| `401` | Unauthorized | No token or invalid token |
| `403` | Forbidden | Token valid, but you lack permission |
| `404` | Not Found | Resource doesn't exist |
| `422` | Unprocessable Entity | Validation failed (wrong email format) |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Bug in our code |

---

## What is a REST API?

**REST** (Representational State Transfer) is a set of design conventions for building APIs. It's not a protocol or a library — it's a style.

Key REST ideas:
1. **Resources**: Everything is a "resource" (user, session, token) identified by a URL
2. **Stateless**: Each request contains all the information needed — the server doesn't remember previous requests
3. **HTTP Methods**: Use GET to read, POST to create, DELETE to delete (don't make everything a POST)
4. **JSON**: Responses are typically in JSON format

```
# RESTful URL design:
POST   /api/v1/auth/signup          → Create a user
POST   /api/v1/auth/login           → Create a session (login)
GET    /api/v1/sessions             → List all sessions
DELETE /api/v1/sessions/{id}        → Delete (revoke) a specific session
GET    /api/v1/users/me             → Get the current user's profile
```

Notice:
- The URL describes the **resource** (what), not the **action** (how)
- The HTTP method describes the **action**
- IDs go in the URL path (`/sessions/{id}`) not in the body

---

## What is FastAPI?

**FastAPI** is a Python web framework for building APIs. It handles:
- Routing (which code runs for which URL)
- Request parsing
- Automatic validation (via Pydantic)
- Automatic API documentation (Swagger UI at `/docs`)
- Dependency injection

### Alternatives to FastAPI

| Framework | Language | Why Not Using It |
|-----------|----------|-----------------|
| **Flask** | Python | Older, sync-only, no built-in validation |
| **Django** | Python | Full-stack (too much), sync-first |
| **Express.js** | JavaScript | Different language |
| **Spring Boot** | Java | Different language, more verbose |
| **Gin** | Go | Different language |

**Why FastAPI?**
- 100% async-native (handles thousands of requests at once)
- Pydantic validation built-in (rejects bad data automatically)
- Auto-generates `/docs` (interactive Swagger UI — what you've been using!)
- Very fast — benchmarks show it close to Node.js

---

## How FastAPI Works

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI(title="AuthForge", version="1.0.0")

@app.get("/health")  # "When someone hits GET /health, run this function"
async def health_check():
    return {"status": "ok"}  # FastAPI auto-converts this dict to JSON
```

### The Lifespan Context Manager

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP code runs here (before the server starts accepting requests)
    async with async_session_maker() as session:
        # Seed default roles if they don't exist
        ...
    
    yield  # Server is now running and handling requests
    
    # SHUTDOWN code runs here (when the server stops)
    await engine.dispose()  # Close all DB connections cleanly

app = FastAPI(lifespan=lifespan)
```

This is AuthForge's startup routine — when the server starts, it automatically seeds the database with the 3 default roles (user, moderator, admin).

---

## What is Uvicorn?

**Uvicorn** is the **server** that actually runs FastAPI. Think of FastAPI as the factory that makes the response, and Uvicorn as the truck that delivers it.

FastAPI itself is just a Python framework — it doesn't know how to listen on a network port. Uvicorn does.

```bash
# How Uvicorn starts our app:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
#          ↑         ↑               ↑              ↑
#     module:object  listen on      on this port  restart when code changes
#                    all interfaces
```

`--reload` is the development flag that makes the server automatically restart when you save a file. In production, you'd remove `--reload`.

---

## Request → Response Flow in AuthForge

```
1. You send: POST http://localhost:8001/api/v1/auth/signup
             Body: {"email": "user@test.com", "password": "mypassword"}
             
2. Uvicorn receives the raw HTTP request

3. FastAPI finds the matching route:
   @router.post("/signup") in app/api/v1/auth.py

4. Pydantic validates the body against UserCreate schema:
   - Is email a valid email? ✓
   - Is password between 8-72 chars? ✓
   
5. FastAPI injects dependencies:
   - db = get_db() → creates an async SQLAlchemy session
   - redis = get_redis() → returns the Redis client

6. Our code runs:
   auth_service = AuthService(db, redis)
   user = await auth_service.signup(user_in)

7. FastAPI serializes the response dict to JSON

8. Uvicorn sends back:
   HTTP/1.1 201 Created
   Content-Type: application/json
   {"user": {...}, "message": "User created successfully..."}
```

---

## Swagger UI at /docs

FastAPI automatically generates an interactive API documentation page.

Visit `http://localhost:8001/docs` when the app is running.

It reads your code — the route decorators, Pydantic schemas, response models — and builds a UI where you can:
- See every endpoint
- Read what input it expects
- Try it out (send real requests)
- See the response

This is possible because FastAPI uses **OpenAPI** (formerly Swagger) under the hood. Every route you define gets added to an auto-generated JSON schema at `/openapi.json`.

---

## CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # In dev: allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**What is CORS?** (Cross-Origin Resource Sharing)

Browsers have a security rule: JavaScript on `site-a.com` cannot call APIs on `site-b.com` by default. This prevents malicious websites from reading your bank balance using your logged-in session.

CORS is a mechanism where the server explicitly says "I allow requests from these specific origins."

In production, you'd change `allow_origins=["*"]` to `allow_origins=["https://yourfrontend.com"]`.

---

## Where FastAPI is Used in AuthForge

| File | Role |
|------|------|
| `app/main.py` | Creates the FastAPI app, adds middleware, includes routers |
| `app/api/v1/auth.py` | Defines auth routes (signup, login, refresh, logout) |
| `app/api/v1/sessions.py` | Defines session routes |
| `app/api/v1/router.py` | Aggregates all route files |
| `app/api/deps.py` | FastAPI dependencies (`get_db`, `get_current_user`) |

---

## Summary

- **HTTP** = the language of the web (request → response)
- **REST** = design conventions for structuring APIs around resources
- **Status codes** = the server's way of saying "what happened" (200 OK, 401 Unauthorized, etc.)
- **FastAPI** = Python framework for building async REST APIs with auto-validation and auto-docs
- **Uvicorn** = the server that runs FastAPI and listens for HTTP connections
- **Swagger UI** = the interactive docs page at `/docs`, auto-generated from your code
- **CORS** = browser security rule; our middleware allows cross-origin requests
