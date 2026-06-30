"""places: user_rating_sum/count 컬럼 추가 + place_rating_reports 테이블 + ratelimit config

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-30
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE places ADD COLUMN IF NOT EXISTS user_rating_sum   INTEGER DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE places ADD COLUMN IF NOT EXISTS user_rating_count INTEGER DEFAULT 0"
    )

    # IP별 장소 rating 이중 반영 방지용 추적 테이블
    op.execute("""
        CREATE TABLE IF NOT EXISTS place_rating_reports (
            ip_hash     VARCHAR(64)  NOT NULL,
            place_id    BIGINT       NOT NULL REFERENCES places(place_id) ON DELETE CASCADE,
            rating_x2   SMALLINT     NOT NULL,  -- rating * 2 (0.5 단위 정수 표현)
            created_at  TIMESTAMPTZ  DEFAULT now(),
            updated_at  TIMESTAMPTZ  DEFAULT now(),
            PRIMARY KEY (ip_hash, place_id)
        )
    """)

    op.execute(
        "INSERT INTO app_config (key, value) "
        "VALUES ('ratelimit.place_report_ip_daily', '\"10\"') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS place_rating_reports")
    op.execute("ALTER TABLE places DROP COLUMN IF EXISTS user_rating_count")
    op.execute("ALTER TABLE places DROP COLUMN IF EXISTS user_rating_sum")
    op.execute(
        "DELETE FROM app_config WHERE key = 'ratelimit.place_report_ip_daily'"
    )
