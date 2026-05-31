# Lesson 19: Role-Based Access Control (RBAC)

---

## What Is RBAC?

RBAC is a security model where users are assigned **roles**, and roles determine what **actions** they can perform. Instead of checking permissions for every individual user, you check their role.

### AuthForge's Three Roles

| Role | Permissions | Who Gets It |
|------|------------|------------|
| **user** (id=1) | View own profile, update own profile | Every new user (default) |
| **moderator** (id=2) | View all users, ban users | Manually promoted by admin |
| **admin** (id=3) | Everything — manage users, change roles, view audit logs | Manually promoted or first user |

### Why Not Just Check `is_admin = True`?

A boolean flag only gives you two levels (admin/not-admin). With roles:
- A **moderator** can view all users but can't change roles
- An **admin** can do everything
- Future roles (e.g., "support", "billing") can be added without changing code

---

## How `require_role` Works

### The Dependency Factory Pattern

```python
def require_role(allowed_roles: List[str]) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker
```

This is called a **factory function** — it's a function that returns another function. When you call `require_role(["admin"])`, it creates a new dependency that:

1. First calls `get_current_user` (validates JWT, loads user)
2. Then checks if the user's role is in the allowed list
3. Returns 403 if not, or returns the user if it is

### Using It in Routes

```python
# Any role can access
@router.get("/users/me")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    ...

# Only admins
@router.get("/admin/users")
async def list_all_users(current_user: User = Depends(require_role(["admin"]))):
    ...

# Admins and moderators
@router.get("/admin/reports")
async def view_reports(current_user: User = Depends(require_role(["admin", "moderator"]))):
    ...
```

---

## Eager Loading: The N+1 Problem

### The Problem

When we load a user from the database, the `role` relationship isn't loaded by default. If we then access `user.role.name`, SQLAlchemy fires a **second query** to fetch the role. This is called the **N+1 problem** — for N users, you get N+1 queries.

### The Fix: `selectinload`

```python
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(User)
    .options(selectinload(User.role))  # ← Load role in the SAME query
    .where(User.id == user_id)
)
```

This tells SQLAlchemy: "When you fetch users, also fetch their roles in one efficient query." Now `user.role.name` works without any extra database call.

We apply this in `get_current_user` so every authenticated request has the role available.

---

## Admin Safety Guards

### Can't Change Your Own Role

```python
if target_user.id == admin_user.id and update_data.role_id is not None:
    raise HTTPException(status_code=400, detail="Cannot change your own role")
```

This prevents an admin from accidentally demoting themselves, which would lock them out of admin features permanently.

### Role Existence Validation

```python
role_result = await session.execute(select(Role).where(Role.id == update_data.role_id))
if not role_result.scalars().first():
    raise HTTPException(status_code=400, detail="Role does not exist")
```

We don't just blindly set `role_id = 999` — we verify the role actually exists in the database first.

---

## Summary

| Concept | What It Does |
|---------|-------------|
| `require_role(["admin"])` | Creates a FastAPI dependency that enforces role-based access |
| `selectinload(User.role)` | Prevents N+1 queries by loading relationships eagerly |
| Self-demotion guard | Prevents admin from locking themselves out |
| Role validation | Verifies the target role exists before changing |
