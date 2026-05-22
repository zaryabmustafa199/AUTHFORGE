"""
Structured logging configuration for AuthForge.

Uses Python's built-in logging module with JSON-formatted output
for production readability and log aggregation compatibility.
"""
import logging
import json
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.
    
    Output example:
    {"timestamp": "2024-01-01T12:00:00Z", "level": "INFO", "logger": "app.services.auth_service", "message": "User login successful", "user_id": "uuid"}
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include any extra fields passed via `logger.info("msg", extra={...})`
        reserved_keys = {
            "name", "msg", "args", "created", "relativeCreated",
            "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "filename", "module", "pathname", "levelname", "levelno",
            "msecs", "process", "processName", "thread", "threadName",
            "taskName", "message",
        }
        for key, value in record.__dict__.items():
            if key not in reserved_keys:
                # Convert UUIDs and other non-serializable objects to strings
                try:
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data, default=str)


def setup_logging(level: str = "INFO") -> None:
    """
    Configures the root logger for the application.
    
    Call this once at app startup (in main.py lifespan).
    """
    root_logger = logging.getLogger("app")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Prevent duplicate handlers if called multiple times
    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a child logger under the 'app' namespace.
    
    Usage:
        from app.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info("User signed up", extra={"user_id": str(user.id)})
    """
    return logging.getLogger(f"app.{name}")
