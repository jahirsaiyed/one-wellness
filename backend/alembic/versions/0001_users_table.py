"""users table — Sprint 1 KAN-19, KAN-20, KAN-21

Revision ID: 0001
Revises:
Create Date: 2026-05-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid() — idempotent
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text, nullable=True),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="client"),
        sa.Column("preferred_language", sa.String(2), nullable=False, server_default="en"),
        sa.Column("timezone", sa.Text, nullable=False, server_default="Asia/Dubai"),
        # 2FA
        sa.Column("totp_secret", sa.Text, nullable=True),
        sa.Column("totp_confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("totp_backup_codes", ARRAY(sa.Text), nullable=True),
        # Google OAuth2
        sa.Column("google_sub", sa.Text, nullable=True, unique=True),
        # Sub-role
        sa.Column("is_safety_officer", sa.Boolean, nullable=False, server_default="false"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('client', 'therapist', 'hr_admin', 'platform_admin')",
    )
    op.create_check_constraint(
        "ck_users_language",
        "users",
        "preferred_language IN ('ar', 'en')",
    )

    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_role", "users", ["role"])
    op.create_index(
        "idx_users_active",
        "users",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # updated_at auto-update trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated_at ON users")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at")
    op.drop_index("idx_users_active", table_name="users")
    op.drop_index("idx_users_role", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
