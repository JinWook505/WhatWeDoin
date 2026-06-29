"""places: theme_tags 컬럼 및 GIN 인덱스 추가

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-29
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE places ADD COLUMN IF NOT EXISTS theme_tags theme_tag[] DEFAULT '{}'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_places_theme ON places USING GIN (theme_tags)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_places_theme")
    op.execute("ALTER TABLE places DROP COLUMN IF EXISTS theme_tags")
