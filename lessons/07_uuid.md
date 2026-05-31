# Lesson 07: UUIDs & Primary Keys

---

## What is a UUID?

**UUID** (Universally Unique Identifier) is a 128-bit number used to uniquely identify things. It looks like:

```
550e8400-e29b-41d4-a716-446655440000
```

That's 32 hexadecimal characters + 4 dashes = 36 characters total.

UUID stands for "Universally Unique" because the probability of two different systems generating the same UUID is astronomically small (about 1 in 2^122 — more atoms than exist in the sun). You can generate UUIDs on two different servers simultaneously and they'll never clash.

---

## The Alternative: Auto-Increment Integer

The other common primary key strategy is a simple auto-incrementing integer:

```sql
id SERIAL PRIMARY KEY  -- 1, 2, 3, 4, 5...
```

Every new row gets the next integer. Simple. Fast. Small storage (4 bytes vs 16 for UUID).

---

## Why UUID is Better for AuthForge

### 1. Security: IDs Are Not Guessable

With integer IDs:
```
GET /api/v1/users/1   → Works (admin user)
GET /api/v1/users/2   → Works (another user)
GET /api/v1/users/3   → Works (another user)
```

An attacker can enumerate users by just incrementing the number. They know user #1 is the first user ever registered (probably the admin!).

With UUIDs:
```
GET /api/v1/users/550e8400-e29b-41d4-a716-446655440000  → Works
GET /api/v1/users/550e8400-e29b-41d4-a716-446655440001  → 404 (doesn't exist)
```

You can't guess a valid UUID.

### 2. No Central Counter Needed

With integer IDs, the database must track the last number used. In a distributed system (multiple servers), coordinating this counter is complex.

With UUIDs, each server generates IDs independently. No coordination needed.

### 3. Safe to Expose in URLs

You can put a UUID in a public URL without revealing how many users you have (competitors would love to see user #1,234 to know your exact user count).

---

## How UUID is Used in AuthForge

```python
# In models/user.py:
import uuid

id = Column(
    UUID(as_uuid=True),         # PostgreSQL UUID column type
    primary_key=True,
    default=uuid.uuid4          # Generate a new UUID when a User is created
)
```

`uuid.uuid4` is the function (not the result!). SQLAlchemy calls it for you each time a new User is created. Version 4 = randomly generated.

```python
# In schemas/user.py:
from uuid import UUID

class UserResponse(BaseModel):
    id: UUID   # Pydantic knows this is a UUID type, validates and serializes correctly
```

When this is returned as JSON:
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com"
}
```

---

## Why Sessions Use UUID Too

```python
# In models/session.py:
id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

When you call `DELETE /api/v1/sessions/some-uuid`, you're revoking a specific session. If session IDs were integers (1, 2, 3...), a user could try to revoke other users' sessions by guessing their IDs. UUIDs make this impossible.

---

## Why AuditLogs Use BigInteger (Not UUID)

```python
# In models/audit_log.py:
id = Column(BigInteger, primary_key=True, index=True)
```

Audit logs are **extremely high-volume**. Every login, logout, password reset, and role change creates an audit log entry. A busy system might generate millions per day.

- UUID: 16 bytes per row
- BigInteger: 8 bytes per row

At 10 million rows, UUID wastes 80MB vs BigInteger. More importantly, BigInteger indexes are faster to query because they're smaller.

For audit logs, you never expose the ID in a public API (no `DELETE /audit_logs/{id}` endpoint), so the security benefit of UUID doesn't apply. Use the storage-efficient option.

---

## UUID Versions

| Version | Generation Method | Use When |
|---------|------------------|---------|
| v1 | Time-based (contains timestamp + MAC address) | Can reveal server info — avoid |
| v4 | Completely random | **Standard for database IDs** (what we use) |
| v5 | Deterministic (namespace + name → UUID) | When same input should always give same UUID |
| v7 | Time-ordered random | Modern databases — sortable AND random |

We use v4 (`uuid.uuid4`) — the industry standard for random, secure IDs.

---

## `as_uuid=True` — What Does This Mean?

```python
Column(UUID(as_uuid=True), ...)
```

PostgreSQL stores UUIDs internally as 16-byte binary values. When Python reads them back:
- `as_uuid=False`: Returns a string like `"550e8400-e29b-41d4-a716-446655440000"`
- `as_uuid=True`: Returns a Python `uuid.UUID` object

We use `as_uuid=True` so we work with real UUID objects in Python, which Pydantic handles correctly in schemas.

---

## Summary

- **UUID**: 128-bit unique identifier — globally unique without a central counter
- **v4 UUID**: Randomly generated — what we use for user and session IDs
- **Security benefit**: Not guessable — can't enumerate users or sessions
- **`as_uuid=True`**: Makes SQLAlchemy return Python `uuid.UUID` objects instead of strings
- **AuditLog uses BigInteger**: High-volume table — 8 bytes is more efficient than 16 bytes for IDs never exposed in public APIs
