# Lesson 02: Environment Variables, .env Files & Secret Keys

---

## What is an Environment Variable?

An **environment variable** is a named value that lives outside your code in the operating system (or container). Instead of writing your database password directly in your Python file, you read it from the environment.

Think of it like a safe next to your code. Your code says "give me the database password from the safe." The safe can hold different values on different machines (dev, staging, production) without changing a single line of code.

```python
# BAD - hardcoded secret in your code:
DATABASE_URL = "postgresql://postgres:mypassword123@localhost:5432/authforge"

# GOOD - read from environment:
import os
DATABASE_URL = os.environ.get("DATABASE_URL")
```

---

## What is a .env File?

A `.env` file is a simple text file that stores environment variables for local development. It lives at the root of your project:

```env
# AuthForge .env file
APP_NAME=AuthForge
SECRET_KEY=d87f2a9b3c1e5f4a8d2b7c9e1f3a5b7d9c2e4f6a8b0d2e4f6a8b0c2d4e6f8a0
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/authforge
REDIS_URL=redis://redis:6379/0
```

The `.env` file is **only for your local machine**. It is **never committed to Git**.

---

## Why NEVER Commit .env to Git?

**Real-world example**: In 2022, a developer at a major company accidentally committed their `.env` file containing AWS credentials to GitHub. Within 4 minutes, automated bots found it. Within 12 minutes, attackers had spun up 100 servers and run up a $50,000 bill.

Your `.env` contains:
- Database passwords (gives full access to all user data)
- Secret keys (allows forging auth tokens)
- OAuth client secrets (allows impersonating your app)

**Protection**:
1. Always add `.env` to `.gitignore`
2. Commit `.env.example` instead — a copy with fake placeholder values, to show other developers what variables are needed

```bash
# .gitignore
.env
*.env
```

---

## What is the .env.example File?

```env
# .env.example — commit this to Git (safe, no real secrets)
APP_NAME=AuthForge
SECRET_KEY=CHANGE_ME_generate_a_real_secret_key
DATABASE_URL=postgresql+asyncpg://postgres:CHANGE_ME@db:5432/authforge
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
MAIL_SERVER=mailhog
MAIL_PORT=1025
MAIL_FROM=noreply@authforge.dev
GOOGLE_CLIENT_ID=CHANGE_ME
GOOGLE_CLIENT_SECRET=CHANGE_ME
```

When a new developer joins the project, they:
1. Copy `.env.example` to `.env`
2. Fill in real values
3. They're ready to run the project

---

## What is a Secret Key?

The `SECRET_KEY` is a long, random string used as the **signing password** for JWT tokens.

When we create a JWT token, we sign it:
```
SIGNATURE = HMAC_SHA256(header + "." + payload, SECRET_KEY)
```

This signature is attached to the token. When a request comes in, we verify:
```
is HMAC_SHA256(header + "." + payload, SECRET_KEY) == signature_in_token?
```

If anyone tampers with the payload (e.g., changes `"role": "user"` to `"role": "admin"`), the signature check fails and the token is rejected.

**The key must be:**
- **Random**: Not a word, not your name
- **Long**: At least 32 bytes (64 hex characters)
- **Secret**: If it leaks, attackers can forge any token

### How to Generate a Good Secret Key

```python
# In Python:
import secrets
print(secrets.token_hex(32))
# Output: a7f3b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1
```

```bash
# Or in terminal:
openssl rand -hex 32
```

---

## Why Different Configs for Dev vs. Production?

| Setting | Development | Production |
|---------|-------------|-----------|
| `DATABASE_URL` | points to Docker `db` container | points to AWS RDS or real server |
| `SECRET_KEY` | any random string | long, cryptographically secure |
| `DEBUG` | True | False |
| `MAIL_SERVER` | `mailhog` (fake) | `smtp.sendgrid.net` (real) |
| `CORS_ORIGINS` | `["*"]` (all allowed) | `["https://yourapp.com"]` (restricted) |

The beauty of environment variables is that you don't change a single line of code — just swap the `.env` values.

---

## How Pydantic Settings Works

Plain `os.environ.get()` has problems:
- Returns `None` silently if the variable is missing
- All values are strings — no type conversion
- No validation or error messages

**`pydantic-settings`** solves all of this:

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "AuthForge"           # Has a default value
    SECRET_KEY: str                        # REQUIRED — no default → crashes if missing
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15 # Automatically converted from string to int!
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str
    REDIS_URL: str

    MAIL_SERVER: str
    MAIL_PORT: int                         # .env has "1025" (string) → int automatically!
    MAIL_FROM: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()  # Created once when the app starts
```

When `Settings()` is instantiated:
1. It reads the `.env` file
2. Validates that all required fields are present
3. Converts types (string "15" → int 15)
4. If `SECRET_KEY` is missing from `.env`, it raises a `ValidationError` immediately with a clear message: *"SECRET_KEY: field required"*

This is called **Fail Fast** — crash early with a clear error rather than mysteriously failing later at runtime.

---

## How the App Reads Settings

```python
# Any file in the project:
from app.config import settings

print(settings.SECRET_KEY)            # The real secret from .env
print(settings.ACCESS_TOKEN_EXPIRE_MINUTES)  # 15 (as int, not string)
```

The `settings` object is created once and imported everywhere. In Python, module-level code runs once. So `settings = Settings()` reads the `.env` file exactly once when the server starts.

---

## Where .env is Used in AuthForge

| Variable | Used In | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | `token_service.py` | Sign and verify JWT tokens |
| `DATABASE_URL` | `database.py` | Connect to PostgreSQL |
| `REDIS_URL` | `redis.py` | Connect to Redis |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `token_service.py` | Set token expiry |
| `MAIL_SERVER` / `MAIL_PORT` | Phase 4 email utils | Connect to MailHog |
| `GOOGLE_CLIENT_ID` | Phase 7 OAuth | Identify our app to Google |

---

## Summary

- **Environment variables**: Config values that live outside code, in the OS or a `.env` file
- **`.env` file**: Local-only config file, NEVER committed to Git
- **`.env.example`**: Template with fake values, ALWAYS committed to Git
- **Secret Key**: Random string used to sign/verify JWTs — if leaked, all tokens can be forged
- **Pydantic `BaseSettings`**: Type-safe, validated config that crashes clearly if required vars are missing
