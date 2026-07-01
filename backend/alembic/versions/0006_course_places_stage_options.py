"""course_places: linear visit_order -> stage_order + option_index (multi-option stages)

SCRUM-78: a course is now a sequence of stages, each stage offering 2-3
alternative places (the user picks one per stage) instead of one fixed
linear path. Existing rows are backfilled as single-option stages.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-01
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE course_places ADD COLUMN IF NOT EXISTS stage_order SMALLINT")
    op.execute("ALTER TABLE course_places ADD COLUMN IF NOT EXISTS option_index SMALLINT NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE course_places ADD COLUMN IF NOT EXISTS stage_label VARCHAR(30) NOT NULL DEFAULT '코스'")

    # Backfill: old rows are 1 place = 1 stage with a single option.
    # stage_label derived from the place's Kakao category via the same mapping
    # backend/app/models/category_labels.py uses at the API layer.
    op.execute("""
        UPDATE course_places cp
        SET stage_order = cp.visit_order,
            stage_label = COALESCE(
                CASE p.category
                    WHEN 'MT1' THEN '대형마트' WHEN 'CS2' THEN '편의점'
                    WHEN 'PS3' THEN '어린이집,유치원' WHEN 'SC4' THEN '학교'
                    WHEN 'AC5' THEN '학원' WHEN 'PK6' THEN '주차장'
                    WHEN 'OL7' THEN '주유소,충전소' WHEN 'SW8' THEN '지하철역'
                    WHEN 'BK9' THEN '은행' WHEN 'CT1' THEN '문화시설'
                    WHEN 'AG2' THEN '중개업소' WHEN 'PO3' THEN '공공기관'
                    WHEN 'AT4' THEN '관광명소' WHEN 'AD5' THEN '숙박'
                    WHEN 'FD6' THEN '음식점' WHEN 'CE7' THEN '카페'
                    WHEN 'HP8' THEN '병원' WHEN 'PM9' THEN '약국'
                    ELSE p.category
                END,
                '코스'
            )
        FROM places p
        WHERE cp.place_id = p.place_id AND cp.stage_order IS NULL
    """)
    # Any leftover rows with no matching place (shouldn't happen, FK-enforced) —
    # fall back to visit_order directly so the NOT NULL below never fails.
    op.execute("UPDATE course_places SET stage_order = visit_order WHERE stage_order IS NULL")

    op.execute("ALTER TABLE course_places ALTER COLUMN stage_order SET NOT NULL")
    op.execute("ALTER TABLE course_places DROP CONSTRAINT IF EXISTS course_places_pkey")
    op.execute("ALTER TABLE course_places ADD PRIMARY KEY (course_id, stage_order, option_index)")
    op.execute("ALTER TABLE course_places DROP COLUMN IF EXISTS visit_order")
    op.execute("ALTER TABLE course_places ALTER COLUMN stage_label DROP DEFAULT")

    # walking_distance_to_next_km ("distance to the next stop") no longer makes
    # sense once a stage has multiple possible next-options — replaced with
    # "distance from the station to this specific option", which is
    # well-defined regardless of which combination across stages gets picked.
    # Existing values are carried over as a placeholder (not recomputed here).
    op.execute(
        "ALTER TABLE course_places RENAME COLUMN walking_distance_to_next_km "
        "TO walking_distance_from_station_km"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE course_places RENAME COLUMN walking_distance_from_station_km "
        "TO walking_distance_to_next_km"
    )
    op.execute("ALTER TABLE course_places ADD COLUMN IF NOT EXISTS visit_order SMALLINT")
    op.execute("UPDATE course_places SET visit_order = stage_order WHERE option_index = 1")
    op.execute("DELETE FROM course_places WHERE option_index <> 1")
    op.execute("ALTER TABLE course_places ALTER COLUMN visit_order SET NOT NULL")
    op.execute("ALTER TABLE course_places DROP CONSTRAINT IF EXISTS course_places_pkey")
    op.execute("ALTER TABLE course_places ADD PRIMARY KEY (course_id, visit_order)")
    op.execute("ALTER TABLE course_places DROP COLUMN IF EXISTS stage_order")
    op.execute("ALTER TABLE course_places DROP COLUMN IF EXISTS option_index")
    op.execute("ALTER TABLE course_places DROP COLUMN IF EXISTS stage_label")
