# Lesson 01: Docker & Docker Compose

---

## What Problem Does Docker Solve?

Imagine you write code on your laptop running Windows. Your teammate has a Mac. Your server runs Linux. The code works on your machine but breaks on theirs. The classic excuse: **"It works on my machine!"**

Or imagine you have three projects:
- Project A needs Python 3.9 + PostgreSQL 14
- Project B needs Python 3.11 + PostgreSQL 16
- Project C needs Python 3.8 + MySQL

Installing all of these on one laptop creates **conflicts**. Libraries overwrite each other. Ports clash. It becomes a mess that is nearly impossible to debug.

**Docker solves this** by wrapping each application and ALL of its dependencies (operating system, runtime, libraries, config) into a sealed, portable box called a **container**. Each container is completely isolated from everything else on your machine.

---

## What is Docker?

Docker is a **containerization platform**. A container is like a lightweight, portable mini-computer that runs inside your real computer.

Think of it this way:
- Your laptop = an apartment building
- Each Docker container = a separate apartment with its own kitchen, bathroom, electricity

The apartments share the building's foundation (the Linux kernel of your OS) but are otherwise completely isolated.

### Key Terms

| Term | What it means |
|------|--------------|
| **Image** | A blueprint/template. Like a recipe. Read-only. |
| **Container** | A running instance of an image. Like a meal cooked from a recipe. |
| **Dockerfile** | Instructions for building a custom image. |
| **Registry** | A store for images (Docker Hub is the public one, like GitHub for images). |

---

## What is Docker Compose?

Docker can run one container at a time. But AuthForge needs 5 services running simultaneously:
- FastAPI app
- PostgreSQL database
- Redis cache
- Celery worker
- MailHog email tester

**Docker Compose** is a tool that lets you define and run **multi-container applications** using a single YAML file (`docker-compose.yml`). It:
1. Starts all containers in the right order
2. Connects them on a private network
3. Mounts your code so changes are reflected live
4. Manages all ports and volumes

---

## Alternatives to Docker

| Alternative | What it is | Why we don't use it |
|-------------|-----------|-------------------|
| **Virtual Machines (VMs)** | Full OS inside your OS (VirtualBox, VMware) | Slow to start, use GBs of RAM each |
| **Conda / virtualenv** | Python-only environment isolation | Only isolates Python, not PostgreSQL/Redis |
| **Install everything natively** | Run Postgres/Redis directly on your OS | Port conflicts, version conflicts, hard to reset |
| **Podman** | Docker alternative, daemonless | Less tooling/documentation for beginners |

**Why Docker?** It's the industry standard. Every company uses it. It isolates everything (not just Python), starts in seconds, and is 100% reproducible.

---

## The Dockerfile (Our Custom Image)

```dockerfile
FROM python:3.11-slim          # Start from the official Python 3.11 image

WORKDIR /app                    # Set the working directory inside the container

RUN apt-get update && apt-get install -y \
    gcc libpq-dev               # Install system libraries needed for PostgreSQL

COPY requirements.txt .         # Copy requirements first (for caching)
RUN pip install --no-cache-dir -r requirements.txt  # Install Python packages

COPY . .                        # Copy all our project code into the container

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Why copy requirements.txt before the code?**
Docker builds images in **layers**. Each instruction creates a layer. If you change your code but not requirements, Docker uses the cached layer for `pip install` (saves minutes of build time). This is called **layer caching**.

---

## Our docker-compose.yml Explained

```yaml
name: authforge       # Unique project name — containers are named authforge-app-1, etc.

services:
  app:                # Our FastAPI application
    build: .          # Build from the Dockerfile in this directory
    ports:
      - "8001:8000"   # Host:Container — access on localhost:8001
    volumes:
      - .:/app        # Sync our Windows folder into /app inside container (hot reload)
    depends_on:
      - db
      - redis
    env_file:
      - .env          # Read environment variables from .env file

  db:                 # PostgreSQL database
    image: postgres:16  # Use the official Postgres image from Docker Hub
    ports:
      - "5433:5432"   # Use 5433 on host to avoid conflicts
    volumes:
      - authforge_postgres_data:/var/lib/postgresql/data  # Persist data across restarts
    environment:
      POSTGRES_DB: authforge
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password

  redis:              # Redis cache
    image: redis:7-alpine
    ports:
      - "6380:6379"

  celery:             # Background task worker
    build: .          # Same image as 'app'
    command: celery -A app.workers.celery_app worker --loglevel=info
    depends_on:
      - redis

  mailhog:            # Fake email server for development
    image: mailhog/mailhog
    ports:
      - "1025:1025"   # SMTP port
      - "8025:8025"   # Web UI to see captured emails
```

### Why Port 8001 Instead of 8000?
You might already have another project running on port 8000. By mapping the host port to 8001, you can run both projects simultaneously without conflicts.

---

## Key Docker Commands

```bash
# Start all services in background
docker-compose up -d

# Start AND rebuild images (after changing Dockerfile or requirements.txt)
docker-compose up -d --build

# Stop and remove containers (data in volumes is preserved)
docker-compose down

# Stop and remove containers AND all data (nuclear reset)
docker-compose down -v

# See logs from the app
docker-compose logs app
docker-compose logs --tail=50 app  # Only last 50 lines

# Run a command inside a running container
docker-compose exec app alembic upgrade head
docker-compose exec app python -c "print('hello')"
docker-compose exec db psql -U postgres authforge  # Open PostgreSQL shell

# See what's running
docker-compose ps
```

---

## Volumes: How Data Persists

Containers are **ephemeral** — when you destroy one, everything inside it disappears.

But your PostgreSQL data must survive container restarts! **Volumes** solve this:

```yaml
volumes:
  - authforge_postgres_data:/var/lib/postgresql/data
```

This maps a **named Docker volume** (managed by Docker on your disk) to the folder inside the container where Postgres stores its data. Even if you `docker-compose down` and restart, your users and data are still there.

The volume `.:/app` in our app service is different — it's a **bind mount** that maps your real Windows folder (`d:\Projects\PORTFOLIO\AUTHFORGE`) to `/app` inside the container. This is what makes hot reload work: you save a file on Windows → the change appears inside the container instantly → Uvicorn detects it and restarts.

---

## Where AuthForge Uses Docker

| File | Purpose |
|------|---------|
| `Dockerfile` | Defines the Python environment and how to start FastAPI |
| `docker-compose.yml` | Orchestrates all 5 services |
| `.env` | Injects config values (database URL, secret key, etc.) |
| `requirements.txt` | All Python packages installed during `docker build` |

---

## Summary

- **Docker** = packaging an app with all its dependencies into an isolated container
- **Image** = the blueprint, **Container** = the running instance
- **Docker Compose** = tool to run multiple containers as a system
- **Volumes** = how data survives container restarts
- **Bind mount** = how your live code changes appear inside the container

Every time you write `docker-compose exec app <command>`, you're reaching inside the running container and running that command in the same environment your FastAPI server runs in. That's why Alembic migrations work — they run inside the container where the Python packages are installed and the database connection is configured.
