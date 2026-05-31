# AuthForge Identity Platform

AuthForge is a production-grade, highly secure authentication and identity management platform. It features a hardened backend built with **FastAPI** (Python) and a modern, pastel-themed frontend built with **React & Vite**.

The system includes Role-Based Access Control (RBAC), Google OAuth 2.0 integration, brute-force protection, rate limiting, and comprehensive audit logging.

---

## 🏗️ Architecture Stack

### Backend
*   **Framework:** FastAPI (Python 3.11+)
*   **Database:** PostgreSQL (with SQLAlchemy ORM & asyncpg)
*   **Caching & Rate Limiting:** Redis
*   **Email:** MailHog (for local OTP development)
*   **Security:** JWT (Stateless), Argon2 hashing, Authlib (OAuth)

### Frontend
*   **Framework:** React 18 + Vite + TypeScript
*   **Styling:** Custom Vanilla CSS (Pastel Theme)
*   **State & Routing:** Context API, React Router v6
*   **API Client:** Axios (with automatic refresh token rotation)

---

## 🚀 Getting Started (How to Run)

To run the full stack locally, you need two terminal windows: one for the Dockerized backend and one for the React frontend.

### 1. Run the Backend (Docker)
Ensure you have Docker and Docker Compose installed. The backend runs entirely inside containers.

1.  **Clone the repository and navigate to the project root:**
    ```bash
    cd AuthForge
    ```
2.  **Set up environment variables:**
    Copy the example `.env` file (if not already done) and configure any secrets (like Google OAuth keys):
    ```bash
    cp .env.example .env
    ```
3.  **Start the services:**
    This command will build and start FastAPI, PostgreSQL, Redis, and MailHog in the background.
    ```bash
    docker-compose up -d --build
    ```
4.  **Backend Services Available At:**
    *   **API Docs (Swagger UI):** http://localhost:8001/docs
    *   **MailHog (View sent emails/OTPs):** http://localhost:8025

### 2. Run the Frontend (React / Vite)
The frontend is run locally using Node.js and NPM.

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```
2.  **Install dependencies (first time only):**
    ```bash
    npm install
    ```
3.  **Start the development server:**
    ```bash
    npm run dev
    ```
4.  **Access the web app:**
    *   Open your browser and go to: **http://localhost:5173**

---

## 🛡️ Security Features

*   **Token Rotation:** Short-lived Access Tokens (15m) and long-lived Refresh Tokens (7d). The frontend automatically intercepts `401 Unauthorized` responses and rotates tokens seamlessly.
*   **Rate Limiting:** IP-based sliding window rate limiter (e.g., max 5 login attempts per minute).
*   **Brute-Force Lockout:** Accounts are temporarily locked (HTTP 423) for 15 minutes after 5 consecutive failed login attempts.
*   **Audit Logging:** An immutable audit trail logs every sensitive action (login, signup, role changes, locks) with IPs and timestamps.
*   **Role-Based Access Control:** Three-tier roles (`user`, `moderator`, `admin`). Admin routes are strictly protected on both backend and frontend.

---

## 🧪 Running Tests
The backend features a robust `pytest` suite ensuring everything works as expected.

To run the tests inside the Docker container:
```bash
docker-compose exec app pytest -v
```

---

## 🛑 Stopping the Application
To stop the backend database and API services, run:
```bash
docker-compose down
```
To stop the frontend, simply press `Ctrl + C` in the terminal where `npm run dev` is running.

## Visual Aesthetics

AuthForge features a highly professional, pristine light-mode aesthetic starring our AuthForge Bodyguard lion:

| Login Page | Sign Up Page |
| :---: | :---: |
| <img src="frontend/src/assets/login-bg.png" width="300"> | <img src="frontend/src/assets/signup-bg.png" width="300"> |

| Verify Email | Dashboard Header |
| :---: | :---: |
| <img src="frontend/src/assets/verify-bg.png" width="300"> | <img src="frontend/src/assets/dashboard-bg.png" width="300"> |

