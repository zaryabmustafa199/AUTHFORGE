from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models here so Alembic can discover them
from .role import Role
from .user import User
from .session import Session
from .audit_log import AuditLog
