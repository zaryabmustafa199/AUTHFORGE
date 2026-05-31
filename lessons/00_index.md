# AuthForge — Lesson Index

A complete curriculum covering every concept used in the AuthForge project.
Read in order for best understanding, or jump to a specific topic.

---

## Lessons

| # | Title | Key Topics |
|---|-------|-----------|
| [01](./01_docker.md) | **Docker & Docker Compose** | Containers, images, volumes, bind mounts, docker-compose.yml, key commands |
| [02](./02_env_and_secrets.md) | **Environment Variables & Secret Keys** | .env files, .env.example, Pydantic Settings, why secrets can't go in Git, how SECRET_KEY works |
| [03](./03_http_and_fastapi.md) | **HTTP, REST APIs & FastAPI** | HTTP methods, status codes, REST design, FastAPI, Uvicorn, Swagger UI, CORS |
| [04](./04_async_programming.md) | **Async Programming** | Blocking vs non-blocking, async/await, event loop, why it matters for web servers |
| [05](./05_databases_postgresql.md) | **Databases & PostgreSQL** | Relational databases, SQL basics, primary keys, foreign keys, JSONB, ACID, TIMESTAMPTZ |
| [06](./06_sqlalchemy_orm.md) | **SQLAlchemy ORM & Models** | ORM concept, Base class, every model in AuthForge explained line by line, relationships |
| [07](./07_uuid.md) | **UUIDs & Primary Keys** | What UUIDs are, v4, security benefits, why AuditLog uses BigInteger instead |
| [08](./08_alembic_migrations.md) | **Alembic & Migrations** | What migrations are, autogenerate workflow, upgrade/downgrade, the env.py fix |
| [09](./09_pydantic_validation.md) | **Pydantic & Data Validation** | Schemas, BaseModel, Field, EmailStr, request vs response schemas, 422 errors |
| [10](./10_password_hashing.md) | **Password Hashing & bcrypt** | Why not plaintext, how hashing works, salts, cost factor, the 72-byte bug we fixed |
| [11](./11_jwt_tokens.md) | **JWT Tokens & Authentication** | Token structure, signing, claims, access vs refresh tokens, HS256, the jti field |
| [12](./12_redis_ttl_blacklist.md) | **Redis, TTL & Token Blacklisting** | In-memory store, TTL concept, blacklisting JTIs, email cooldowns, rate limiting with Redis |
| [13](./13_sessions_token_rotation.md) | **Sessions & Token Rotation** | Session table purpose, rotation explained, why immediate revocation isn't instant, session endpoints |
| [14](./14_dependency_injection.md) | **FastAPI Dependency Injection** | Depends(), get_db, get_redis, get_current_user, OAuth2PasswordBearer, require_role |
| [15](./15_repository_service_pattern.md) | **Repository & Service Architecture** | 3-layer pattern, what goes where, how all layers connect for signup/login |
| [16](./16_rbac_ratelimit_celery_oauth.md) | **RBAC, Rate Limiting, Celery & OAuth** | Role-based access, rate limiting with Redis, audit logging, background tasks, Google OAuth flow |
| [17](./17_email_celery_verification.md) | **Email Verification & Celery** | Background task queues, MailHog, OTP generation, and password reset flows |
| [18](./18_production_code_quality.md) | **Production Code Quality** | Exception handling, structured logging, global error handlers, transaction safety, CORS, security headers, Celery retries, input validation |
| [19](./19_rbac.md) | **Role-Based Access Control** | require_role dependency factory, eager loading, admin routes, self-demotion guard, role validation |
| [20](./20_security_hardening.md) | **Security Hardening** | Redis rate limiting, brute-force lockout, audit logging, security headers, fail-open vs fail-closed |
| [21](./21_google_oauth.md) | **Google OAuth 2.0** | Authorization code flow, token exchange, account linking, 3 user scenarios, authlib integration |
| [22](./22_testing.md) | **Automated Testing** | pytest, async fixtures, dependency overrides, database isolation, test patterns |

---

## Suggested Reading Order

### If you're completely new (start here):
1. → Lesson 03 (What even is an API?)
2. → Lesson 01 (What is Docker?)
3. → Lesson 02 (What is .env?)
4. → Lesson 05 (What is a Database?)
5. → Lesson 10 (Why we hash passwords)
6. → Lesson 11 (What is a JWT?)
7. → Continue in order from Lesson 04

### If you understand web basics, do it in order:
01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15 → 16

---

## Concepts Quick-Reference

| Term | Lesson |
|------|--------|
| `async def` / `await` | 04 |
| `alembic revision --autogenerate` | 08 |
| `bcrypt` / password hashing | 10 |
| `BIGINT` vs `UUID` for primary keys | 07 |
| Celery workers | 16 |
| CORS | 03 |
| `Depends()` | 14 |
| Docker volumes | 01 |
| Email cooldown (Redis) | 12 |
| Foreign keys / `CASCADE` / `SET NULL` | 05 |
| `get_current_user` | 14 |
| JSONB column | 05, 06 |
| JWT structure (header.payload.signature) | 11 |
| `jti` field | 11, 12 |
| MailHog | 16 |
| `metadata_info` (not `metadata`) | 06 |
| OAuth 2.0 | 16 |
| ORM | 06 |
| Pydantic `Field(min_length, max_length)` | 09 |
| RBAC | 16 |
| Rate limiting | 16 |
| Redis TTL | 12 |
| `require_role()` | 14, 16 |
| Repository pattern | 15 |
| `SECRET_KEY` | 02, 11 |
| Service layer | 15 |
| Sessions table | 13 |
| Token blacklisting | 12 |
| Token rotation | 13 |
| UUID v4 | 07 |
| `.env` file | 02 |
