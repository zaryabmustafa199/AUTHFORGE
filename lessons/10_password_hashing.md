# Lesson 10: Password Hashing & bcrypt

---

## Why You NEVER Store Plaintext Passwords

Imagine your database is stolen. If passwords are stored plaintext:

```
email                  | password
-----------------------|----------
alice@example.com      | mypassword123
bob@example.com        | ilovecats!
charlie@example.com    | qwerty456
```

The attacker now has EVERYONE's password. Worse — most people reuse passwords. They can try the same password on Gmail, banks, social media. This is a **credential stuffing attack**.

Real-world examples of plaintext password disasters:
- **RockYou (2009)**: 32 million passwords leaked in plaintext
- **Adobe (2013)**: 153 million records, poorly hashed
- **LinkedIn (2012)**: 6.5 million unsalted SHA-1 hashes — cracked in days

---

## What is Hashing?

A **hash function** is a one-way transformation:

```
"mypassword123"  → hash → "$2b$12$KIXsVJUxj4..."

"$2b$12$KIXsVJUxj4..."  → hash → ???  (can't reverse it!)
```

You can go forward (plaintext → hash) but NOT backward (hash → plaintext). To verify a password, you hash what the user enters and compare it to the stored hash.

```python
# Sign up:
hashed = hash("mypassword123")     # Store this hash
# Store "$2b$12$KIXsVJUxj4..." in DB

# Login attempt:
user_typed = "mypassword123"
is_correct = verify("mypassword123", "$2b$12$KIXsVJUxj4...")  # True ✓
is_correct = verify("wrongpassword", "$2b$12$KIXsVJUxj4...")  # False ✗
```

---

## Why Not Simple Hash Functions (MD5, SHA-1, SHA-256)?

These are cryptographic hash functions, but they're **too fast** for passwords:

- SHA-256 can hash 10 BILLION passwords per second on a modern GPU
- An attacker with a database of hashes can try every common password in seconds
- Pre-computed "rainbow tables" map billions of common passwords to their hashes

---

## What is bcrypt?

**bcrypt** is a password hashing algorithm specifically designed to be **slow**. It takes about 100-300ms to hash a password. That's fine for login (user doesn't notice). But for an attacker:

- 300ms per attempt = only 3 attempts per second
- Dictionary of 10 million common passwords = 34 days to crack one hash
- Modern systems with thousands of users = practically impossible

### bcrypt Output Looks Like

```
$2b$12$KIXsVJUxj4...long_random_string...
│  │   │
│  │   └─ 53-character random salt
│  └───── cost factor (2^12 = 4096 iterations)
└──────── bcrypt version identifier
```

### The Salt

A **salt** is random data mixed into the password before hashing. Even if two users have the same password, their hashes will be different because each salt is unique:

```
User A: hash("password" + "random_salt_1") = "$2b$12$AAAA..."
User B: hash("password" + "random_salt_2") = "$2b$12$BBBB..."
```

This defeats pre-computed rainbow tables. An attacker must hash every password separately for each user.

### The Cost Factor

```
$2b$12$...
        ↑
    cost = 12 → 2^12 = 4096 rounds of hashing
```

Higher cost = slower = more secure. As computers get faster, you can increase the cost factor. bcrypt is designed to stay secure as hardware improves.

---

## How We Use It in AuthForge

```python
# app/utils/security.py
from passlib.context import CryptContext

# Configure: use bcrypt scheme, auto-deprecate older schemes
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
    # Takes "mypassword123", generates a random salt, hashes 4096 times
    # Returns: "$2b$12$KIXsVJUxj4AKxrBjQeJ0vu..."

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
    # Extracts salt from hash, re-hashes the plain password, compares
    # Returns True/False
```

### Where It's Called

**Signup** (creating a user):
```python
# app/repositories/user_repo.py
async def create(self, user_in: UserCreate) -> User:
    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),  # Hash before saving!
        full_name=user_in.full_name
    )
```

**Login** (verifying a password):
```python
# app/services/auth_service.py
async def login(self, email: str, password: str) -> dict:
    user = await self.user_repo.get_by_email(email)
    if not verify_password(password, user.hashed_password):  # Compare with hash
        raise HTTPException(401, "Incorrect email or password")
```

**Refresh token validation** (comparing hashed refresh tokens in sessions):
```python
# app/services/auth_service.py
for sess in active_sessions:
    if verify_password(refresh_token, sess.refresh_token_hash):  # Token hash comparison
        current_session = sess
        break
```

---

## Why Are Refresh Tokens Also Hashed?

We store a **bcrypt hash of the refresh token** in the `sessions` table, not the raw token.

If the database is stolen:
- **Unhashed tokens**: Attacker has all refresh tokens, can log in as any user
- **Hashed tokens**: Attacker has hashes of tokens they can't reverse — useless

Same principle as passwords. If it's a secret that could grant access, hash it.

---

## The Bug We Fixed: bcrypt's 72-Character Limit

**What happened**: When you tried to sign up with a very long password, the server crashed.

**Root cause**: bcrypt has a hard limit of 72 bytes. Any bytes beyond 72 are silently ignored. Newer versions of the `bcrypt` library throw an error instead of silently truncating.

**Two-layer fix we applied**:

1. **Pydantic validation** (prevents bad data from reaching the hash function):
```python
password: str = Field(..., min_length=8, max_length=72)
```

2. **Library version pin** (fixes `passlib`'s internal startup test):
```python
# requirements.txt
passlib[bcrypt]==1.7.4
bcrypt==3.2.2   # ← Pinned to version compatible with passlib's startup test
```

The technical bug: `passlib` runs an internal self-test during startup where it hashes a 73-character string to detect a known bcrypt bug ("wrap bug"). Newer `bcrypt` versions (4.x) reject passwords > 72 bytes instead of truncating, causing this startup test to crash. Pinning to `bcrypt==3.2.2` uses the older behavior that `passlib` expects.

---

## Summary

- **Never store plaintext passwords** — if the DB is stolen, everyone is compromised
- **Hashing** = one-way transformation; you can verify but not reverse
- **bcrypt** = deliberately slow hash algorithm designed for passwords; resists brute-force
- **Salt** = random data added to each hash; prevents rainbow table attacks
- **Cost factor** = how many rounds of hashing; increase over time as hardware improves
- **`get_password_hash()`** = used when creating a user and storing a session's token
- **`verify_password()`** = used during login and refresh token validation
- **72-byte limit** = bcrypt's architectural limit; we enforce it in Pydantic schema
- **Refresh tokens hashed** = same principle as passwords; if DB stolen, tokens are useless
