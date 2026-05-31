# Lesson 17: Email Verification, Password Reset & Celery

---

## Why Use Background Tasks?

When a user signs up, we need to send them a welcome/verification email. If we send the email directly in the FastAPI request handler:
1. The user clicks "Sign Up".
2. The server creates the user in the database.
3. The server connects to the SMTP server (email provider).
4. The server waits for the email to send (this can take 2-5 seconds).
5. The server returns a success response.

**The Problem**: The user had to wait 5 seconds! If the email server is down, the whole signup process fails.

**The Solution**: Background Tasks.
We use **Celery** to say: *"Hey, put this email task in a queue. I'll respond to the user immediately, and you handle the email whenever you have a chance."*

---

## What is Celery?

Celery is an asynchronous task queue/job queue based on distributed message passing.

It requires a **Message Broker**. A message broker is the middleman between your web app (FastAPI) and your workers (Celery). We use **Redis** as our message broker.

### The Flow:
1. **FastAPI** says: `send_verification_email.delay("user@example.com", "123456")`
2. **Redis** receives this message and holds it in a queue.
3. **Celery Worker** (running in its own Docker container) constantly watches Redis. It sees the message, picks it up, and actually sends the email.

---

## How It's Implemented in AuthForge

### 1. The Celery App (`app/workers/celery_app.py`)

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "authforge_tasks",
    broker=settings.CELERY_BROKER_URL,       # redis://redis:6379/1
    backend=settings.CELERY_RESULT_BACKEND,  # redis://redis:6379/2
    include=["app.workers.tasks"]
)
```
*Notice we use Redis database 1 for the broker and 2 for results, separating it from our app data on database 0.*

### 2. The Tasks (`app/workers/tasks.py`)

```python
from celery import shared_task
from app.utils.email import send_email_sync

@shared_task(name="app.workers.tasks.send_verification_email")
def send_verification_email(email: str, otp: str):
    # This function runs in the background worker!
    html_body = f"<h2>Your OTP is: {otp}</h2>"
    send_email_sync(to_email=email, subject="Verify Account", html_body=html_body)
```

### 3. Calling the Task (`app/services/auth_service.py`)

```python
async def signup(self, user_in: UserCreate) -> User:
    user = await self.user_repo.create(user_in)
    
    # 1. Generate OTP
    otp = generate_otp()
    
    # 2. Hash it and store in Redis (10 min TTL)
    hashed_otp = get_password_hash(otp)
    await self.redis.setex(f"verify:{user.id}", 600, hashed_otp)
    
    # 3. Queue the background task!
    send_verification_email.delay(user.email, otp)
    
    return user
```
Using `.delay()` is the magic word that sends it to Redis instead of running it immediately.

---

## MailHog: Testing Emails Without Spamming

During development, we don't want to accidentally send real emails (or pay for an email service like SendGrid).

We use **MailHog**, an email testing tool for developers. It acts like a real SMTP server, but instead of sending emails to the real world, it traps them and displays them in a web interface.

In our `docker-compose.yml`:
```yaml
  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025" # SMTP server (where our app sends emails)
      - "8025:8025" # Web UI (where we view the emails)
```

You can view the emails by opening `http://localhost:8025` in your browser!

---

## Email Verification Flow

1. **User signs up**.
2. **Server** generates a 6-digit numeric OTP.
3. **Server** hashes the OTP (just like a password) and saves it in Redis with a 10-minute TTL.
4. **Celery** emails the unhashed OTP to the user.
5. **User** submits the OTP to `/verify-email`.
6. **Server** gets the hash from Redis, verifies the user's OTP against the hash, sets `is_verified = True`, and deletes the OTP from Redis.

Why hash the OTP? If an attacker hacks our Redis database, they'll only get hashes, not the actual verification codes!

---

## Password Reset Flow

Very similar, but we use a longer, secure URL-safe token instead of a 6-digit numeric code.

1. **User requests reset** at `/forgot-password`.
2. **Server** generates a secure 32-byte string (`secrets.token_urlsafe(32)`).
3. **Server** hashes it and saves it in Redis (15-minute TTL).
4. **Celery** emails the token to the user.
5. **User** submits the new password and token to `/reset-password`.
6. **Server** verifies the token.
7. **Security Feature**: If successful, the server revokes ALL active sessions for that user. This ensures that if their account was compromised, the attacker is immediately kicked out on all devices!

---

## Rate Limiting & Cooldowns

What stops a bot from hitting `/forgot-password` 10,000 times a second and sending 10,000 emails?

We implemented a **cooldown** mechanism using Redis.

```python
cooldown_key = f"email_cooldown:{user.id}"
if await self.redis.exists(cooldown_key):
    raise HTTPException(status_code=429, detail="Please wait before requesting another email")

# If no cooldown, set one for 60 seconds
await self.redis.setex(cooldown_key, 60, "1")
```
Now, users can only request one email every 60 seconds. Simple and effective!

---

## Summary

- **Celery**: Background task worker. Keeps APIs fast by offloading slow tasks.
- **Redis**: Acts as our Message Broker (queueing tasks) and Cache (storing OTPs/Cooldowns).
- **MailHog**: Traps emails in development so we can view them at `http://localhost:8025`.
- **OTP Security**: Always hash OTPs and Reset Tokens before storing them.
- **Session Revocation**: Changing a password should always log the user out of all other devices.
- **Cooldowns**: Simple Redis TTLs prevent email spam abuse.
