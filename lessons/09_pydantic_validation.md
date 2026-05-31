# Lesson 09: Pydantic & Data Validation

---

## The Problem: Trusting User Input

Users send data to your API. That data can be:
- Wrong type: `{"age": "not a number"}`
- Missing required fields: `{"name": "John"}` (forgot email)
- Malformed: `{"email": "notanemail"}`
- Too long: `{"password": "a" * 10000}` (potential buffer overflow attack)

Without validation, your code crashes with confusing errors deep in the stack. Or worse — invalid data gets saved to your database.

**Pydantic** is a Python library that validates data according to rules you define, before your business logic even runs.

---

## What is Pydantic?

Pydantic uses Python type hints to define data shapes and validate them automatically.

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr                             # Must be a valid email
    password: str = Field(min_length=8, max_length=72)  # 8-72 chars
    full_name: Optional[str] = None            # Optional, defaults to None
```

When FastAPI receives a request body `{"email": "notanemail", "password": "hi"}`, Pydantic automatically:
1. Checks `email` → not valid email → Error!
2. Checks `password` → less than 8 chars → Error!

FastAPI returns a `422 Unprocessable Entity` response with detailed error info:
```json
{
    "detail": [
        {"loc": ["body", "email"], "msg": "not a valid email address", "type": "value_error"},
        {"loc": ["body", "password"], "msg": "ensure this value has at least 8 characters"}
    ]
}
```

All of this happens automatically, before your code runs.

---

## Pydantic vs. Raw Python

**Without Pydantic** (manual validation):
```python
def signup(email, password):
    if not email or "@" not in email:
        raise ValueError("Invalid email")
    if len(password) < 8:
        raise ValueError("Password too short")
    if len(password) > 72:
        raise ValueError("Password too long")
    # What about None values? What about wrong types? This gets ugly fast...
```

**With Pydantic**:
```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
# That's it. Pydantic handles all the error cases automatically.
```

---

## Key Pydantic Concepts

### BaseModel

```python
class UserCreate(BaseModel):
    ...
```

Every Pydantic schema inherits from `BaseModel`. This gives it validation, serialization, and deserialization capabilities.

### Field

`Field()` adds extra rules to a field:

```python
from pydantic import Field

password: str = Field(
    ...,               # '...' means REQUIRED (no default)
    min_length=8,      # Minimum 8 characters
    max_length=72,     # Maximum 72 characters (bcrypt limit)
    description="User's password"  # Shows up in Swagger docs
)
```

### Optional

```python
from typing import Optional
full_name: Optional[str] = None  # Can be None, defaults to None
```

### EmailStr

```python
from pydantic import EmailStr
email: EmailStr  # Validates it contains @ and a valid domain
```

### ConfigDict (Pydantic v2)

```python
from pydantic import ConfigDict

class UserResponse(BaseModel):
    id: UUID
    email: str
    
    model_config = ConfigDict(from_attributes=True)
    #                          ↑
    # Allows reading from SQLAlchemy model objects, not just dicts
```

Without `from_attributes=True`, you'd have to manually convert SQLAlchemy objects to dicts before returning them. With it, Pydantic reads the SQLAlchemy object's attributes directly.

---

## All AuthForge Schemas Explained

### `schemas/user.py`

```python
class UserBase(BaseModel):
    # Shared fields used by multiple user schemas
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    # Used for POST /signup request body
    # Inherits email + full_name from UserBase
    password: str = Field(..., min_length=8, max_length=72)

class UserUpdate(BaseModel):
    # Used for PATCH /users/me request body
    # All fields optional — only send what you want to change
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    # What we RETURN to the client — notice hashed_password is NOT here!
    # The client never sees the password hash
    id: UUID
    is_verified: bool
    is_active: bool
    role_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    # Allows: return user_db_object (SQLAlchemy) → automatically serialized
```

**Key insight**: We have separate schemas for REQUEST (what we accept) and RESPONSE (what we return). The `UserResponse` intentionally excludes `hashed_password` — even if a hacker intercepts the response, they don't get the password hash.

### `schemas/auth.py`

```python
class Token(BaseModel):
    # What we return after successful login
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # Always "bearer" — standard OAuth2 convention

class TokenData(BaseModel):
    # Internal schema for decoded JWT payload
    user_id: Optional[str] = None
    email: Optional[str] = None

class LoginRequest(BaseModel):
    # Used for JSON login (not used with OAuth2PasswordRequestForm)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)

class SignupResponse(BaseModel):
    # What we return after successful signup
    user: UserResponse         # Nested schema — the user details
    message: str = "User created successfully. Please verify your email."
```

### `schemas/session.py`

```python
class SessionResponse(BaseModel):
    # What we return when listing active sessions
    id: UUID
    device_info: Optional[str] = None    # "Chrome on Windows"
    ip_address: Optional[str] = None     # "192.168.1.1"
    is_revoked: bool
    created_at: datetime
    expires_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```

Notice: `refresh_token_hash` is NOT in `SessionResponse`. The hash never leaves the server.

---

## Request vs. Response Schemas

This is a critical security and design pattern:

| Schema | Direction | Contains |
|--------|-----------|---------|
| `UserCreate` | → Server | email, password (plaintext, validated) |
| `UserResponse` | Client ← | email, id, is_verified (NO password hash) |
| `LoginRequest` | → Server | email, password |
| `Token` | Client ← | access_token, refresh_token |
| `SessionResponse` | Client ← | id, device, ip, dates (NO token hash) |

The response schemas act as a **security filter** — sensitive internal data (password hashes, token hashes) never reaches the client.

---

## How FastAPI + Pydantic Work Together

```python
@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(
    user_in: UserCreate,      # ← Pydantic validates the request body against UserCreate
    db: AsyncSession = Depends(get_db)
):
    user = await auth_service.signup(user_in)
    return {"user": user}     # ← FastAPI validates this against SignupResponse
                              #   and filters out any extra fields
```

FastAPI:
1. Parses the JSON body and validates it against `UserCreate`
2. If validation fails → auto 422 response
3. If validation passes → calls your function
4. Takes your return value and validates it against `SignupResponse`
5. Filters to only include fields defined in `SignupResponse`
6. Serializes to JSON and returns

The `response_model=SignupResponse` is a **double guarantee**: even if you accidentally return a database object with a password hash, FastAPI will filter it out.

---

## Summary

- **Pydantic**: Auto-validates incoming data against type hints and Field rules
- **`BaseModel`**: Parent class for all schemas
- **`Field(...)`**: `...` means required; add `min_length`, `max_length`, `description`
- **`Optional[str] = None`**: Field is optional, defaults to None
- **`EmailStr`**: Validates email format
- **`ConfigDict(from_attributes=True)`**: Let Pydantic read SQLAlchemy model attributes directly
- **Request schemas**: What we accept from clients (UserCreate, LoginRequest)
- **Response schemas**: What we return (UserResponse, Token) — a security filter that excludes sensitive fields
- **422 Unprocessable Entity**: Automatic response when validation fails — you don't write this code
