"""stations (external_source, external_id) unique constraint 추가

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-29
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE stations ADD CONSTRAINT uq_stations_external UNIQUE (external_source, external_id)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE stations DROP CONSTRAINT IF EXISTS uq_stations_external")
