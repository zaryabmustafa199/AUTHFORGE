# Lesson 06: SQLAlchemy ORM & Models

---

## What is an ORM?

**ORM** stands for Object-Relational Mapper. It's a library that lets you work with database tables as if they were Python classes and objects — without writing raw SQL.

**Without ORM** (raw SQL):
```python
import psycopg2
conn = psycopg2.connect("...")
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
row = cursor.fetchone()
# row is just a tuple: ('uuid', 'email@test.com', True, ...)
# You must manually map each value to a variable
```

**With SQLAlchemy ORM**:
```python
result = await session.execute(select(User).where(User.email == email))
user = result.scalars().first()
# user is a real Python object:
print(user.email)       # "email@test.com"
print(user.is_verified) # True
print(user.created_at)  # datetime(2024, 1, 1, ...)
```

No raw SQL. The database result becomes a typed Python object with real attributes.

---

## Alternatives to SQLAlchemy

| Library | Language | Notes |
|---------|---------|-------|
| **SQLAlchemy** | Python | Most powerful, full-featured, industry standard |
| **Django ORM** | Python | Only works with Django |
| **Tortoise ORM** | Python | Async-first, simpler, less features |
| **Peewee** | Python | Lightweight, sync-only |
| **Prisma** | TypeScript | Type-safe, code-generation based |

**Why SQLAlchemy?**
- Works with FastAPI (unlike Django ORM)
- Supports async (version 2.0+)
- Massive ecosystem and documentation
- Used at NASA, Reddit, Yelp, OpenStack

---

## How SQLAlchemy Works: The Base Class

```python
# app/models/__init__.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

`Base` is the foundation. Every model (table) inherits from it. SQLAlchemy tracks all subclasses of `Base` and knows which tables exist.

```python
# app/models/user.py
from . import Base  # Import the shared Base

class User(Base):   # Inherits from Base → "this is a database table"
    __tablename__ = "users"  # The actual table name in PostgreSQL
    ...
```

---

## The User Model: Line by Line

```python
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),              # PostgreSQL UUID type; Python uuid.UUID objects
        primary_key=True,                 # This is the unique identifier
        default=uuid.uuid4               # Auto-generate a UUID when creating
    )
    
    email = Column(
        String(255),                      # VARCHAR(255)
        unique=True,                      # No two users can share an email
        nullable=False,                   # NOT NULL — required
        index=True                        # Create a database index for fast lookups
    )
    
    hashed_password = Column(
        String(255),
        nullable=True                     # NULL for OAuth-only users (no password)
    )
    
    full_name = Column(String(100), nullable=True)
    
    is_verified = Column(Boolean, default=False)   # Email not verified by default
    is_active = Column(Boolean, default=True)      # Active by default
    
    role_id = Column(
        Integer,
        ForeignKey("roles.id"),           # Must exist in the roles table
        default=1                         # Default role is 1 = "user"
    )
    
    oauth_provider = Column(String(20), nullable=True)     # "google" or NULL
    oauth_provider_id = Column(String(255), nullable=True) # Google's user ID
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()         # PostgreSQL sets this automatically
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()               # Auto-update when row changes
    )
    
    # Relationships (not columns — they're virtual Python attributes)
    role = relationship("Role", back_populates="users")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
```

---

## The Role Model: Line by Line

```python
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)  # Auto-incrementing int (1, 2, 3)
    # Note: No 'default=uuid4' here — roles use simple integers
    
    name = Column(
        String(50),
        unique=True,                 # "user", "moderator", "admin" — each unique
        nullable=False
    )
    
    permissions = Column(
        JSONB,                       # A JSON array of permission strings
        default=list                 # Default: empty list []
    )
    
    users = relationship("User", back_populates="role")
```

**Pre-seeded roles** (created in `main.py` on startup):
```python
Role(name="user",      permissions=["read_own", "write_own"])
Role(name="moderator", permissions=["read_all", "ban_users"])
Role(name="admin",     permissions=["read_all", "write_all", "manage_users", "manage_roles"])
```

---

## The Session Model: Line by Line

```python
class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),   # Delete sessions when user deleted
        nullable=False
    )
    
    refresh_token_hash = Column(String(255), nullable=False)
    # SECURITY: We never store the raw token. We store a bcrypt hash.
    # This means if the DB is stolen, tokens are still safe.
    
    device_info = Column(String(255), nullable=True)
    # Example: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    ip_address = Column(String(45), nullable=True)
    # Why 45? IPv6 addresses are up to 39 chars, but mapped IPv4 is 45:
    # "::ffff:192.168.1.1" is 19 chars, max IPv6 = 39
    
    is_revoked = Column(Boolean, default=False)
    # False = active session. True = logged out.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    # Set to "now + 7 days" when the session is created
    
    user = relationship("User", back_populates="sessions")
```

---

## The AuditLog Model: Line by Line

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        BigInteger,                       # NOT UUID — why?
        primary_key=True,
        index=True
    )
    # Why BigInteger instead of UUID?
    # Audit logs are HIGH VOLUME — every login, logout, password reset creates one.
    # BigInteger auto-increments (1, 2, 3, ...) and is more storage-efficient than UUID
    # (8 bytes vs 16 bytes). At millions of rows, this matters.
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),   # Keep log even if user deleted
        nullable=True   # NULL when user_id set to NULL after user deletion
    )
    
    action = Column(String(100), nullable=False)
    # Examples: "LOGIN", "LOGOUT", "PASSWORD_RESET", "EMAIL_VERIFIED", "ROLE_CHANGED"
    
    ip_address = Column(String(45), nullable=True)
    
    metadata_info = Column(JSONB, default=dict)
    # Why "metadata_info" not "metadata"?
    # "metadata" is a RESERVED WORD in SQLAlchemy's Base class.
    # Using it as a column name would cause a conflict!
    # This is a real gotcha that caught us — fixed by renaming to metadata_info.
    # Example value: {"user_agent": "Mozilla/...", "location": "Karachi, PK"}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="audit_logs")
```

---

## What is a Relationship?

`relationship()` creates a virtual attribute — it's not a column in the database. It tells SQLAlchemy how to JOIN tables together.

```python
# In User model:
sessions = relationship("Session", back_populates="user")

# In Session model:
user = relationship("User", back_populates="sessions")
```

Now you can do:
```python
user = await user_repo.get_by_id("some-uuid")
print(user.sessions)   # List of all Session objects for this user!
# SQLAlchemy automatically runs: SELECT * FROM sessions WHERE user_id = 'some-uuid'
```

`back_populates` links the relationship in both directions. Setting it on one model also updates the other.

---

## How SQLAlchemy Translates to SQL

When you write:
```python
result = await session.execute(select(User).where(User.email == email))
```

SQLAlchemy generates this SQL and sends it to PostgreSQL:
```sql
SELECT users.id, users.email, users.hashed_password, users.full_name, 
       users.is_verified, users.is_active, users.role_id, ...
FROM users
WHERE users.email = 'user@example.com'
```

---

## The Session (Database Session vs. User Session)

**Confusing term alert!** The word "session" means two different things:

| Context | Meaning |
|---------|---------|
| `AsyncSession` (SQLAlchemy) | A database connection "unit of work" — a transaction context |
| `Session` model (our code) | A record in the `sessions` table representing a user's logged-in device |

```python
# SQLAlchemy's AsyncSession:
async with async_session_maker() as session:  # Database transaction
    result = await session.execute(...)        # Execute SQL query
    await session.commit()                     # Commit to database

# Our Session model:
db_session = Session(user_id=user.id, refresh_token_hash="...")  # User's login
```

---

## Summary

- **ORM**: Maps database tables to Python classes — no raw SQL needed
- **`Base`**: The parent class all models inherit from; SQLAlchemy tracks all subclasses
- **`Column`**: Defines a column in the table — type, constraints, defaults
- **`relationship()`**: Virtual attribute that auto-fetches related rows from other tables
- **`primary_key`**: The unique identifier for each row
- **`ForeignKey`**: Links a column to another table's primary key; enforces referential integrity
- **`server_default=func.now()`**: Let PostgreSQL auto-set timestamp columns
- **`JSONB`**: Stores flexible JSON data that can be queried and indexed
- **`BigInteger` for audit_logs**: High-volume tables use integers for storage efficiency
- **`metadata_info` not `metadata`**: Reserved word in SQLAlchemy — must rename
