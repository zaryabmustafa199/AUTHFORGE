# Lesson 21: Google OAuth 2.0 — "Login with Google"

---

## What Is OAuth?

OAuth 2.0 is a standard protocol that lets users log into your app using their existing Google/GitHub/Facebook account, **without giving you their password**.

Instead of:
```
User → types password → Your app verifies it
```

OAuth does:
```
User → redirected to Google → Google verifies identity → Google tells your app "this user is legit"
```

### Why Use It?

| Benefit | Explanation |
|---------|------------|
| No password to store | Less security liability for you |
| Instant trust | Google has already verified their email |
| Lower friction | One click instead of filling out a form |
| Better security | Google's auth infrastructure is battle-tested |

---

## The Authorization Code Flow (Step by Step)

This is the most secure OAuth flow. It has 4 steps:

```
┌──────┐         ┌──────────┐         ┌────────┐
│ User │         │ AuthForge │         │ Google │
└──┬───┘         └────┬─────┘         └───┬────┘
   │  Click "Login     │                   │
   │  with Google"     │                   │
   │──────────────────>│                   │
   │                   │  Redirect to      │
   │                   │  Google consent   │
   │<──────────────────│                   │
   │                   │                   │
   │  User grants      │                   │
   │  permission       │                   │
   │──────────────────────────────────────>│
   │                   │                   │
   │                   │  Google redirects  │
   │                   │  back with CODE   │
   │<──────────────────────────────────────│
   │                   │                   │
   │                   │  Exchange code    │
   │                   │  for tokens       │
   │                   │──────────────────>│
   │                   │                   │
   │                   │  Google returns   │
   │                   │  user info        │
   │                   │<──────────────────│
   │                   │                   │
   │  JWT tokens       │                   │
   │<──────────────────│                   │
```

### Step 1: Redirect to Google

```
GET /api/v1/auth/oauth/google
→ Redirects to: https://accounts.google.com/o/oauth2/v2/auth
  ?client_id=YOUR_ID
  &redirect_uri=http://localhost:8001/api/v1/auth/oauth/google/callback
  &scope=openid email profile
  &response_type=code
```

### Step 2: User Grants Permission

Google shows a consent screen: "AuthForge wants to access your email and profile." The user clicks "Allow."

### Step 3: Google Redirects Back With a Code

```
GET /api/v1/auth/oauth/google/callback?code=4/0AXE...
```

This `code` is a **one-time authorization code**. It's NOT a token — it can only be used once to exchange for real tokens.

### Step 4: Exchange Code for User Info

Our backend sends the code to Google (server-to-server, not through the browser):

```python
token_response = await client.fetch_token(GOOGLE_TOKEN_URL, code=code)
user_info = await client.get("https://www.googleapis.com/oauth2/v3/userinfo")
# Returns: {"sub": "12345", "email": "user@gmail.com", "name": "John"}
```

Then we create/find the user and issue our own JWT tokens.

---

## The Three User Scenarios

### Scenario 1: Returning Google User

User has logged in with Google before. We find them by email → their `oauth_provider` is already "google" → just log them in.

### Scenario 2: Existing Password User

User signed up with email/password, now clicks "Login with Google." Same email exists, but no `oauth_provider` set. We **link** the Google account:

```python
existing_user.oauth_provider = "google"
existing_user.oauth_provider_id = google_id
existing_user.is_verified = True  # Google verified their email
```

Now the user can log in with **either** password or Google.

### Scenario 3: Brand New User

No account with this email exists. We create a new user:

```python
new_user = User(
    email=google_email,
    full_name=google_name,
    hashed_password=None,    # No password — OAuth only
    oauth_provider="google",
    oauth_provider_id=google_id,
    is_verified=True,        # Google verified
)
```

This user can only log in via Google (no password set).

---

## Security Considerations

| Concern | How We Handle It |
|---------|-----------------|
| Code interception | Code is exchanged server-to-server (not exposed to the browser) |
| Fake Google callbacks | `client_secret` is required for the exchange — only our server has it |
| Email spoofing | We trust Google's email verification, not user input |
| Account takeover | We check `oauth_provider_id` matches, not just email |
| Missing credentials | Returns 501 (Not Implemented) if GOOGLE_CLIENT_ID isn't configured |

---

## Setting Up Google OAuth (When You're Ready)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Go to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth 2.0 Client IDs**
5. Set application type to **Web application**
6. Add authorized redirect URI: `http://localhost:8001/api/v1/auth/oauth/google/callback`
7. Copy `Client ID` and `Client Secret` into your `.env`:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8001/api/v1/auth/oauth/google/callback
```

---

## Summary

| Component | Role |
|-----------|------|
| `OAuthService.get_google_auth_url()` | Builds the consent URL |
| `OAuthService.google_callback()` | Exchanges code → finds/creates user → issues JWT |
| `OAuthService._find_or_create_user()` | Handles all 3 user scenarios |
| `authlib` library | Handles the OAuth protocol details (token exchange, signing) |
| `httpx` library | Makes async HTTP requests to Google's API |
