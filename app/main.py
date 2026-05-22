"""
AuthForge — FastAPI Application Factory.

Configures the application lifespan, middleware, exception handlers,
and route registration.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from app.database import async_session_maker, engine
from app.models.role import Role
from app.config import settings
from app.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    setup_logging(level=settings.LOG_LEVEL)
    logger.info("AuthForge starting up")

    try:
        async with async_session_maker() as session:
            result = await session.execute(select(Role))
            roles = result.scalars().all()
            if not roles:
                default_roles = [
                    Role(name="user", permissions=["read_own", "write_own"]),
                    Role(name="moderator", permissions=["read_all", "ban_users"]),
                    Role(name="admin", permissions=["read_all", "write_all", "manage_users", "manage_roles"]),
                ]
                session.add_all(default_roles)
                await session.commit()
                logger.info("Seeded default roles: user, moderator, admin")
            else:
                logger.info("Roles already exist, skipping seed", extra={"role_count": len(roles)})
    except SQLAlchemyError as exc:
        logger.error("Failed to seed roles — database may be unreachable", extra={"error": str(exc)})
        raise

    yield

    # ── Shutdown ──
    await engine.dispose()
    logger.info("AuthForge shut down")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Grade Authentication & Identity Platform",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catches any unhandled exception and returns a clean JSON response
    instead of leaking stack traces to the client.
    """
    logger.error(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "error": str(exc),
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Catches database-level errors (connection failures, constraint violations
    that slip past service-layer validation) and returns a clean response.
    """
    logger.error(
        "Database error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "error": str(exc),
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "A database error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
# CORS — origins configurable via ALLOWED_ORIGINS in .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ---------------------------------------------------------------------------
# Route Registration
# ---------------------------------------------------------------------------
from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
