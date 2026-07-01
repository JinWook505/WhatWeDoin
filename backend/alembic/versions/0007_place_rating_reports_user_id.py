"""place_rating_reports: user_id 컬럼 추가 (로그인/비로그인 구분 저장)

SCRUM-90: place_rating_reports는 PK가 (ip_hash, place_id)뿐이라 로그인 사용자도
IP 기준으로만 중복이 방지됐음 (같은 IP를 공유하는 여러 로그인 사용자가 각자
평가할 수 없었음). course_reviews와 동일하게 user_id/ip_hash를 분리 저장하도록
surrogate id 기반으로 전환.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-02
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE place_rating_reports DROP CONSTRAINT place_rating_reports_pkey")
    op.execute("ALTER TABLE place_rating_reports ADD COLUMN id BIGSERIAL PRIMARY KEY")
    op.execute("ALTER TABLE place_rating_reports ADD COLUMN user_id BIGINT REFERENCES users(id)")
    op.execute("ALTER TABLE place_rating_reports ALTER COLUMN ip_hash DROP NOT NULL")
    op.execute(
        "ALTER TABLE place_rating_reports ADD CONSTRAINT chk_place_rating_reporter "
        "CHECK (user_id IS NOT NULL OR ip_hash IS NOT NULL)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_place_rating_report_user ON place_rating_reports (user_id, place_id) "
        "WHERE user_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_place_rating_report_ip ON place_rating_reports (ip_hash, place_id) "
        "WHERE user_id IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_place_rating_report_ip")
    op.execute("DROP INDEX IF EXISTS uq_place_rating_report_user")
    op.execute("ALTER TABLE place_rating_reports DROP CONSTRAINT IF EXISTS chk_place_rating_reporter")
    op.execute("DELETE FROM place_rating_reports WHERE ip_hash IS NULL")
    op.execute("ALTER TABLE place_rating_reports ALTER COLUMN ip_hash SET NOT NULL")
    op.execute("ALTER TABLE place_rating_reports DROP COLUMN user_id")
    op.execute("ALTER TABLE place_rating_reports DROP COLUMN id")
    op.execute("ALTER TABLE place_rating_reports ADD PRIMARY KEY (ip_hash, place_id)")
