# Lesson 08: Alembic & Database Migrations

---

## The Problem: Code vs. Database are Out of Sync

You have Python models (code) and a running PostgreSQL database. When you add a new column to a model:

```python
# You added this to the User model:
phone_number = Column(String(20), nullable=True)
```

Your Python code now expects a `phone_number` column. But the actual database table doesn't have it yet. If you try to insert a user, it will fail.

You need a way to **apply model changes to the database** in a controlled, trackable, reversible way. This is what **database migrations** are for.

---

## What is Alembic?

**Alembic** is a database migration tool for SQLAlchemy. It:

1. **Detects** the difference between your SQLAlchemy models and the actual database schema
2. **Generates** a Python script that describes the changes needed ("the migration")
3. **Applies** those changes to the database
4. **Tracks** which migrations have been applied (in a `alembic_version` table)
5. **Allows rollback** — you can undo migrations

---

## Alternatives to Alembic

| Tool | Used With | Notes |
|------|---------|-------|
| **Alembic** | SQLAlchemy | Most powerful, auto-detects changes |
| **Django Migrations** | Django ORM | Only for Django |
| **Flyway** | Any SQL | Write raw SQL migration files |
| **Liquibase** | Any SQL | Enterprise-grade, XML-based |
| **Prisma Migrate** | Prisma | TypeScript ORM |

**Why Alembic?** It's the standard for SQLAlchemy projects. Auto-generation saves enormous time.

---

## The Alembic Files in AuthForge

```
alembic/
├── env.py                    ← Configuration for Alembic
├── script.py.mako            ← Template for new migration files
└── versions/
    └── 02ca9c111647_initial_commit.py  ← Our first (and so far only) migration
alembic.ini                   ← Alembic's main config file
```

### `alembic.ini`

```ini
[alembic]
script_location = alembic        # Where migration files are stored
sqlalchemy.url = driver://...    # Database connection (we override this in env.py)
```

### `alembic/env.py` (The Important One)

```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ↑ Add parent directory to Python path so we can import 'app.models'

from app.config import settings
from app.models import Base  # Import ALL models (they register with Base automatically)

# This is what Alembic uses to detect schema differences:
target_metadata = Base.metadata
```

We had to add the `sys.path.insert` fix because when Alembic runs inside Docker, it starts from `/app` but needs to find the `app` package. Without this, it would get `ModuleNotFoundError: No module named 'app'`.

---

## The Migration Workflow

### Step 1: Generate a Migration

```bash
docker-compose exec app alembic revision --autogenerate -m "Initial commit"
```

What `--autogenerate` does:
1. Reads all models registered with `Base` (User, Role, Session, AuditLog)
2. Compares them to what's actually in the database (currently nothing)
3. Generates a Python file that describes what SQL to run

Output in terminal:
```
INFO Detected added table 'roles'
INFO Detected added table 'users'
INFO Detected added table 'audit_logs'
INFO Detected added table 'sessions'
Generating /app/alembic/versions/02ca9c111647_initial_commit.py ... done
```

The file `02ca9c111647_initial_commit.py` was created with the prefix `02ca9c111647` — a random hex ID that orders migrations.

### Step 2: Apply the Migration

```bash
docker-compose exec app alembic upgrade head
```

`head` means "apply all unapplied migrations, up to the latest one."

What happens:
1. Alembic reads the `alembic_version` table in PostgreSQL (creates it if it doesn't exist)
2. Sees which migrations have been applied
3. Runs the ones that haven't been applied yet (in order)

Output:
```
INFO Running upgrade → 02ca9c111647, Initial commit
```

Now the `users`, `roles`, `sessions`, and `audit_logs` tables exist in the database!

---

## Inside a Migration File

```python
# alembic/versions/02ca9c111647_initial_commit.py

revision = '02ca9c111647'   # This migration's ID
down_revision = None         # None = this is the first migration

def upgrade() -> None:
    # This SQL runs when you apply the migration
    op.create_table('roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('permissions', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        ...
    )
    ...

def downgrade() -> None:
    # This SQL runs when you UNDO the migration
    op.drop_table('sessions')
    op.drop_table('audit_logs')
    op.drop_table('users')
    op.drop_table('roles')
```

Every migration has `upgrade()` (apply) and `downgrade()` (undo). This means you can go forward AND backward in history.

---

## Common Alembic Commands

```bash
# Generate a new migration from model changes
docker-compose exec app alembic revision --autogenerate -m "Add phone_number to users"

# Apply all pending migrations
docker-compose exec app alembic upgrade head

# Undo the last migration
docker-compose exec app alembic downgrade -1

# See migration history
docker-compose exec app alembic history

# See current applied version
docker-compose exec app alembic current

# Apply up to a specific revision
docker-compose exec app alembic upgrade 02ca9c111647
```

---

## The Golden Rules of Migrations

1. **Never manually edit the database** — all changes go through migrations
2. **Never delete migration files** — they're the history of your schema
3. **Commit migration files to Git** — other developers need them
4. **Review auto-generated migrations before applying** — Alembic is good but not perfect
5. **One migration per feature** — don't put unrelated changes in one file

---

## Real-World Workflow

```
1. You add a column to a SQLAlchemy model (in Python)
2. docker-compose exec app alembic revision --autogenerate -m "Add phone to user"
3. Review the generated file in alembic/versions/
4. docker-compose exec app alembic upgrade head  (applies it to dev DB)
5. git add alembic/versions/  (commit the migration file)
6. When deploying to production: alembic upgrade head runs automatically
```

---

## Summary

- **Migration**: A script that describes changes to a database schema
- **Alembic**: SQLAlchemy's migration tool — auto-detects model changes and generates SQL
- **`revision --autogenerate`**: Compare models to DB and generate a migration script
- **`upgrade head`**: Apply all pending migrations to the database
- **`downgrade -1`**: Undo the last migration
- **`env.py`**: Connects Alembic to our SQLAlchemy models; we fixed it by adding the Python path
- **Never manually change the DB**: All schema changes go through Alembic migrations
