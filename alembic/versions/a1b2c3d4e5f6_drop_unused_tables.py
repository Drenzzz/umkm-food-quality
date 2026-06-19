"""drop_unused_password_resets_and_email_verifications

Revision ID: a1b2c3d4e5f6
Revises: f7b2c4d5e6a1
Create Date: 2026-06-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f7b2c4d5e6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_email_verifications_token_hash", table_name="email_verifications")
    op.drop_index("ix_email_verifications_user_id", table_name="email_verifications")
    op.drop_index("ix_email_verifications_id", table_name="email_verifications")
    op.drop_table("email_verifications")

    op.drop_index("ix_password_resets_token_hash", table_name="password_resets")
    op.drop_index("ix_password_resets_user_id", table_name="password_resets")
    op.drop_index("ix_password_resets_id", table_name="password_resets")
    op.drop_table("password_resets")


def downgrade() -> None:
    op.create_table(
        "password_resets",
        op.Column("id", op.Integer(), nullable=False),
        op.Column("user_id", op.Integer(), nullable=False),
        op.Column("token_hash", op.String(length=64), nullable=False),
        op.Column("expires_at", op.DateTime(timezone=True), nullable=False),
        op.Column("used_at", op.DateTime(timezone=True), nullable=True),
        op.Column("created_at", op.DateTime(timezone=True), server_default=op.text("now()"), nullable=False),
        op.ForeignKeyConstraint(["user_id"], ["users.id"]),
        op.PrimaryKeyConstraint("id"),
        op.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_password_resets_id", "password_resets", ["id"])
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])
    op.create_index("ix_password_resets_token_hash", "password_resets", ["token_hash"], unique=True)

    op.create_table(
        "email_verifications",
        op.Column("id", op.Integer(), nullable=False),
        op.Column("user_id", op.Integer(), nullable=False),
        op.Column("token_hash", op.String(length=64), nullable=False),
        op.Column("expires_at", op.DateTime(timezone=True), nullable=False),
        op.Column("verified_at", op.DateTime(timezone=True), nullable=True),
        op.Column("created_at", op.DateTime(timezone=True), server_default=op.text("now()"), nullable=False),
        op.ForeignKeyConstraint(["user_id"], ["users.id"]),
        op.PrimaryKeyConstraint("id"),
        op.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_email_verifications_id", "email_verifications", ["id"])
    op.create_index("ix_email_verifications_user_id", "email_verifications", ["user_id"])
    op.create_index("ix_email_verifications_token_hash", "email_verifications", ["token_hash"], unique=True)
