"""add_last_password_change_at

Revision ID: 9a2b7d4c1e88
Revises: 475f9b21a9b1
Create Date: 2026-05-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9a2b7d4c1e88"
down_revision: Union[str, Sequence[str], None] = "475f9b21a9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_password_change_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_password_change_at")
