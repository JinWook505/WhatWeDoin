"""course_review_reports 및 report_reason enum 삭제 (미사용 리뷰 신고 기능 제거)

SCRUM-91: course_review_reports 테이블과 POST .../reviews/{review_id}/report
엔드포인트가 존재했지만, 프론트엔드 어디에서도 호출하지 않는 죽은 코드로 확인되어
제거한다.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-02
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS course_review_reports")
    op.execute("DROP TYPE IF EXISTS report_reason")


def downgrade() -> None:
    op.execute("""
        CREATE TYPE report_reason AS ENUM ('SPAM', 'INAPPROPRIATE', 'WRONG_INFO', 'OTHER')
    """)
    op.execute("""
        CREATE TABLE course_review_reports (
            id          BIGSERIAL PRIMARY KEY,
            review_id   BIGINT NOT NULL REFERENCES course_reviews(id) ON DELETE CASCADE,
            user_id     BIGINT REFERENCES users(id),
            ip_hash     VARCHAR(64),
            reason      report_reason NOT NULL,
            comment     TEXT,
            created_at  TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT chk_reporter CHECK (user_id IS NOT NULL OR ip_hash IS NOT NULL)
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX uq_report_user ON course_review_reports (review_id, user_id) "
        "WHERE user_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_report_ip ON course_review_reports (review_id, ip_hash) "
        "WHERE user_id IS NULL"
    )
