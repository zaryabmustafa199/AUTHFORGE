# Lesson 05: Databases & PostgreSQL

---

## What is a Database?

A **database** is an organized collection of data that can be stored, retrieved, updated, and deleted efficiently. Think of it as a super-powered Excel spreadsheet that can handle millions of rows, multiple related tables, and thousands of simultaneous users.

Without a database, all your data lives in Python variables — and disappears the moment the server restarts.

---

## Types of Databases

| Type | Examples | Best For |
|------|---------|---------|
| **Relational (SQL)** | PostgreSQL, MySQL, SQLite | Structured data with relationships |
| **Document (NoSQL)** | MongoDB, CouchDB | Flexible, schema-less documents |
| **Key-Value** | Redis, DynamoDB | Fast lookups by key |
| **Graph** | Neo4j | Connected data (social networks) |
| **Time-Series** | InfluxDB | Metrics, logs |

---

## Why PostgreSQL?

PostgreSQL is an open-source **relational database**. It stores data in **tables** (like spreadsheets) with defined **columns** (like column headers). Rows in different tables can be **related** via foreign keys.

**Why PostgreSQL specifically?**

| Feature | PostgreSQL | MySQL | SQLite |
|---------|-----------|-------|--------|
| JSONB (JSON columns) | ✅ Native, indexed | ❌ Basic JSON | ❌ No |
| UUID support | ✅ Native | Partial | ❌ |
| Full ACID compliance | ✅ | Partial (MyISAM) | ✅ |
| Production-ready | ✅ | ✅ | ❌ (file-based) |
| Used by | Instagram, Airbnb, GitHub | WordPress, YouTube | Mobile apps |

We chose PostgreSQL because:
1. JSONB support (used for `permissions` in roles and `metadata` in audit logs)
2. UUID as a native column type
3. Industry standard for production web applications
4. Full async support via `asyncpg`

---

## What is SQL?

**SQL** (Structured Query Language) is the language used to talk to relational databases.

```sql
-- Create a table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert a row
INSERT INTO users (id, email) VALUES ('...uuid...', 'user@example.com');

-- Read rows
SELECT * FROM users WHERE email = 'user@example.com';

-- Update a row
UPDATE users SET is_verified = true WHERE id = '...uuid...';

-- Delete a row
DELETE FROM users WHERE id = '...uuid...';
```

We don't write raw SQL in AuthForge — we use SQLAlchemy ORM (covered in the next lesson). But understanding SQL helps you understand what's happening under the hood.

---

## What is a Primary Key?

A **primary key** is a column (or combination of columns) that **uniquely identifies** every row in a table. No two rows can have the same primary key value.

```sql
-- In the users table:
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
--  ↑                          ↑
-- The unique ID column     Auto-generated when a row is inserted
```

Every time a new user is created, PostgreSQL automatically generates a unique UUID for the `id` column. You never have to set it manually.

---

## What is a Foreign Key?

A **foreign key** creates a relationship between two tables. It says: "This column's value must exist in another table."

```sql
-- In the sessions table:
user_id UUID REFERENCES users(id) ON DELETE CASCADE
--      ↑        ↑         ↑              ↑
-- The column  Points to  users table    If the user is deleted,
--             the users  primary key    delete their sessions too
```

This means you cannot create a session for a user that doesn't exist — the database will reject it. This is called **referential integrity** — the database enforces the rules for you.

### Cascade Options

| Option | Meaning |
|--------|---------|
| `ON DELETE CASCADE` | Delete child rows when parent is deleted |
| `ON DELETE SET NULL` | Set the FK column to NULL when parent is deleted |
| `ON DELETE RESTRICT` | Prevent deleting parent if children exist |

In AuthForge:
- `sessions.user_id` has `CASCADE` — delete user → delete their sessions
- `audit_logs.user_id` has `SET NULL` — delete user → keep the audit log, but set user_id to NULL (for historical records)

---

## AuthForge's Table Structure

```
┌─────────────┐      ┌─────────────────┐      ┌──────────────────┐
│    roles    │      │     users       │      │    sessions      │
├─────────────┤      ├─────────────────┤      ├──────────────────┤
│ id (PK)     │◄─────│ role_id (FK)    │◄─────│ user_id (FK)     │
│ name        │      │ id (UUID PK)    │      │ id (UUID PK)     │
│ permissions │      │ email           │      │ refresh_token... │
└─────────────┘      │ hashed_password │      │ device_info      │
                     │ is_verified     │      │ is_revoked       │
                     │ is_active       │      │ expires_at       │
                     └─────────────────┘      └──────────────────┘
                              │
                              │ (SET NULL)
                              ▼
                     ┌──────────────────┐
                     │   audit_logs     │
                     ├──────────────────┤
                     │ id (BigInt PK)   │
                     │ user_id (FK/NUL) │
                     │ action           │
                     │ metadata_info    │
                     └──────────────────┘
```

---

## What is JSONB?

**JSONB** (JSON Binary) is a PostgreSQL column type that stores JSON data. Unlike storing JSON as a plain string, JSONB:
1. **Validates** the JSON is valid when inserting
2. **Stores it in binary** format for faster access
3. **Allows indexing** on specific JSON keys
4. **Allows querying** inside the JSON

```python
# In the Role model:
permissions = Column(JSONB, default=list)

# Example value:
# ["read_own", "write_own"]
# or
# ["read_all", "write_all", "manage_users", "manage_roles"]
```

We use JSONB for `permissions` because the list of permissions can vary per role, and we might want to query "find all roles that have the `manage_users` permission" efficiently.

```sql
-- Query all roles with manage_users permission:
SELECT * FROM roles WHERE permissions ? 'manage_users';
```

---

## Data Types Used in AuthForge

| Column | SQL Type | Explanation |
|--------|---------|-------------|
| `id` on users/sessions | `UUID` | Globally unique identifier (covered in Lesson 06) |
| `id` on audit_logs | `BIGINT` | Large auto-incrementing integer (high-volume table) |
| `email` | `VARCHAR(255)` | Variable-length string, max 255 chars |
| `is_verified` | `BOOLEAN` | true/false |
| `created_at` | `TIMESTAMPTZ` | Timestamp WITH timezone |
| `permissions` | `JSONB` | JSON stored in binary format |
| `metadata_info` | `JSONB` | Flexible extra data per audit event |

### Why TIMESTAMPTZ (With Timezone)?

Always store timestamps in UTC with timezone information. Without timezone, "2024-01-01 12:00:00" is ambiguous — is that noon in Pakistan, London, or New York?

`TIMESTAMPTZ` stores the timezone offset and lets you convert to any timezone on retrieval.

---

## The `server_default=func.now()` Pattern

```python
created_at = Column(DateTime(timezone=True), server_default=func.now())
```

This tells PostgreSQL to automatically set `created_at` to the current timestamp **at the database level** when a row is inserted. You never have to pass `created_at` in your code — the database handles it.

`func.now()` in SQLAlchemy translates to `NOW()` in PostgreSQL SQL.

---

## ACID Properties

PostgreSQL is **ACID compliant**, which is the gold standard for database reliability:

| Property | Meaning | Real Example |
|----------|---------|-------------|
| **Atomicity** | All operations in a transaction succeed, or none do | Bank transfer: debit AND credit happen together, or neither |
| **Consistency** | Data always follows rules (constraints) | You can't insert a session for a non-existent user |
| **Isolation** | Concurrent transactions don't interfere | Two users signing up simultaneously don't corrupt each other's data |
| **Durability** | Committed data survives crashes | After `commit()`, data is safe even if the server dies |

---

## Summary

- **Database**: Persistent, organized storage for application data
- **PostgreSQL**: Industry-standard relational database with UUID, JSONB, full ACID compliance
- **Table**: Like a spreadsheet — columns (fields) and rows (records)
- **Primary Key**: Uniquely identifies each row (users use UUID, audit_logs use BigInt)
- **Foreign Key**: Links rows across tables; database enforces referential integrity
- **JSONB**: PostgreSQL's fast, queryable JSON column type (used for permissions and metadata)
- **TIMESTAMPTZ**: Always store timestamps with timezone (UTC)
