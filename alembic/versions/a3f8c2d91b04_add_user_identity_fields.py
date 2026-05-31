"""add user identity fields

Revision ID: a3f8c2d91b04
Revises: 02ca9c111647
Create Date: 2026-05-31

Adds username (unique, indexed), phone_number, and date_of_birth columns
to the users table. All columns are nullable to allow safe migration of
existing data and OAuth users.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a3f8c2d91b04"
down_revision: Union[str, None] = "02ca9c111647"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("phone_number", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "phone_number")
    op.drop_column("users", "username")
