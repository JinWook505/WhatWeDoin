"""Add withdrawn_at to users; make recommendation_requests.user_id nullable

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-01
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS withdrawn_at TIMESTAMPTZ")
    op.execute(
        "ALTER TABLE recommendation_requests ALTER COLUMN user_id DROP NOT NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE recommendation_requests ALTER COLUMN user_id SET NOT NULL"
    )
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS withdrawn_at")
