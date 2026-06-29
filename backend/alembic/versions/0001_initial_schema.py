"""Initial schema: all tables, enums, PostGIS indexes

Revision ID: 0001
Revises:
Create Date: 2026-06-29
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ── Enum types ──────────────────────────────────────────────────────────
    op.execute("CREATE TYPE oauth_provider AS ENUM ('KAKAO', 'NAVER')")
    op.execute("CREATE TYPE gender_type AS ENUM ('MALE', 'FEMALE', 'OTHER', 'UNKNOWN')")
    op.execute("CREATE TYPE dating_stage AS ENUM ('SOME', 'EARLY', 'LONGTERM', 'UNKNOWN')")
    op.execute(
        "CREATE TYPE budget_tier AS ENUM "
        "('UNDER_30000', '30000_70000', '70000_150000', 'OVER_150000')"
    )
    op.execute(
        "CREATE TYPE companion_type AS ENUM ('SOLO', 'FRIEND', 'COUPLE', 'FAMILY')"
    )
    op.execute(
        "CREATE TYPE theme_tag AS ENUM ("
        "'FOOD', 'CAFE', 'BAR', 'BOARD_GAME', 'KARAOKE', 'ARCADE', "
        "'PARK', 'CULTURE', 'SHOPPING', 'NIGHT_VIEW', 'MOVIE', 'ACTIVITY')"
    )
    op.execute("CREATE TYPE served_from AS ENUM ('LLM', 'CACHE')")
    op.execute(
        "CREATE TYPE report_reason AS ENUM "
        "('SPAM', 'INAPPROPRIATE', 'WRONG_INFO', 'OTHER')"
    )

    # ── stations ─────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE stations (
            station_id      BIGSERIAL PRIMARY KEY,
            external_id     VARCHAR(64),
            external_source oauth_provider,
            name            VARCHAR(100) NOT NULL,
            lat             DOUBLE PRECISION NOT NULL,
            lng             DOUBLE PRECISION NOT NULL,
            geom            GEOGRAPHY(Point, 4326) NOT NULL,
            is_supported    BOOLEAN DEFAULT TRUE,
            created_at      TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_stations_geom ON stations USING GIST (geom)")

    op.execute("""
        CREATE TABLE station_lines (
            station_id  BIGINT REFERENCES stations(station_id),
            line_no     VARCHAR(20) NOT NULL,
            PRIMARY KEY (station_id, line_no)
        )
    """)

    # ── users ────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE users (
            id                       BIGSERIAL PRIMARY KEY,
            oauth_provider           oauth_provider NOT NULL DEFAULT 'KAKAO',
            oauth_id                 VARCHAR(255) NOT NULL,
            email                    VARCHAR(255),
            nickname                 VARCHAR(50) NOT NULL,
            profile_image_url        TEXT,
            gender                   gender_type DEFAULT 'UNKNOWN',
            birth_year               SMALLINT,
            dating_stage             dating_stage DEFAULT 'UNKNOWN',
            preferred_companion_type companion_type,
            preferred_theme_tags     theme_tag[] DEFAULT '{}',
            preferred_budget         budget_tier,
            home_station_id          BIGINT REFERENCES stations(station_id),
            terms_agreed_at          TIMESTAMPTZ NOT NULL,
            privacy_agreed_at        TIMESTAMPTZ NOT NULL,
            marketing_agreed         BOOLEAN DEFAULT FALSE,
            marketing_agreed_at      TIMESTAMPTZ,
            status                   VARCHAR(20) DEFAULT 'ACTIVE',
            last_login_at            TIMESTAMPTZ,
            created_at               TIMESTAMPTZ DEFAULT now(),
            updated_at               TIMESTAMPTZ DEFAULT now(),
            UNIQUE (oauth_provider, oauth_id)
        )
    """)

    # ── courses ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE courses (
            course_id                 BIGSERIAL PRIMARY KEY,
            station_id                BIGINT NOT NULL REFERENCES stations(station_id),
            theme_tags                theme_tag[] NOT NULL DEFAULT '{}',
            budget_tier               budget_tier NOT NULL,
            companion_type            companion_type NOT NULL,
            head_count                SMALLINT,
            query_text                TEXT,
            places                    JSONB NOT NULL,
            total_walking_distance_km NUMERIC(4,1),
            rating_count              INTEGER DEFAULT 0,
            rating_sum                INTEGER DEFAULT 0,
            bayesian_score            NUMERIC(5,2) DEFAULT 0,
            content_hash              VARCHAR(64) UNIQUE,
            created_at                TIMESTAMPTZ DEFAULT now(),
            updated_at                TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_courses_station ON courses (station_id)")
    op.execute("CREATE INDEX idx_courses_theme ON courses USING GIN (theme_tags)")
    op.execute(
        "CREATE INDEX idx_courses_rank ON courses (station_id, bayesian_score DESC)"
    )
    op.execute(
        "CREATE INDEX idx_courses_filter ON courses (budget_tier, companion_type, head_count)"
    )

    # ── places ───────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE places (
            place_id        BIGSERIAL PRIMARY KEY,
            external_id     VARCHAR(64) NOT NULL,
            external_source oauth_provider NOT NULL,
            name            VARCHAR(200) NOT NULL,
            category        VARCHAR(50),
            address         TEXT,
            lat             DOUBLE PRECISION NOT NULL,
            lng             DOUBLE PRECISION NOT NULL,
            geom            GEOGRAPHY(Point, 4326) NOT NULL,
            price_range     VARCHAR(50),
            business_hours  JSONB,
            map_url         TEXT,
            phone           VARCHAR(30),
            thumbnail_url   TEXT,
            status          VARCHAR(10) DEFAULT 'OPEN',
            last_synced_at  TIMESTAMPTZ,
            created_at      TIMESTAMPTZ DEFAULT now(),
            updated_at      TIMESTAMPTZ DEFAULT now(),
            UNIQUE (external_source, external_id)
        )
    """)
    op.execute("CREATE INDEX idx_places_geom ON places USING GIST (geom)")
    op.execute("CREATE INDEX idx_places_category ON places (category)")

    # ── course_places ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE course_places (
            course_id                   BIGINT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
            visit_order                 SMALLINT NOT NULL,
            place_id                    BIGINT NOT NULL REFERENCES places(place_id),
            description                 TEXT,
            walking_distance_to_next_km NUMERIC(4,1),
            created_at                  TIMESTAMPTZ DEFAULT now(),
            PRIMARY KEY (course_id, visit_order)
        )
    """)
    op.execute(
        "CREATE INDEX idx_course_places_place ON course_places (place_id)"
    )

    # ── recommendation_requests ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE recommendation_requests (
            id                BIGSERIAL PRIMARY KEY,
            user_id           BIGINT NOT NULL REFERENCES users(id),
            station_id        BIGINT NOT NULL REFERENCES stations(station_id),
            query_text        TEXT NOT NULL,
            parsed_input      JSONB,
            exclude_place_ids BIGINT[] DEFAULT '{}',
            served_from       served_from NOT NULL,
            idempotency_key   VARCHAR(64),
            course_id         BIGINT REFERENCES courses(course_id),
            created_at        TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX uq_rec_idem ON recommendation_requests (user_id, idempotency_key) "
        "WHERE idempotency_key IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX idx_rec_recent ON recommendation_requests (user_id, created_at DESC)"
    )

    # ── course_reviews ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE course_reviews (
            id          BIGSERIAL PRIMARY KEY,
            course_id   BIGINT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
            user_id     BIGINT REFERENCES users(id),
            ip_hash     VARCHAR(64),
            score       SMALLINT NOT NULL,
            comment     TEXT,
            links       JSONB NOT NULL DEFAULT '[]',
            created_at  TIMESTAMPTZ DEFAULT now(),
            updated_at  TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT chk_review_identity CHECK (user_id IS NOT NULL OR ip_hash IS NOT NULL),
            CONSTRAINT chk_review_score CHECK (score BETWEEN 0 AND 100 AND score % 5 = 0)
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX uq_review_user ON course_reviews (course_id, user_id) "
        "WHERE user_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_review_ip ON course_reviews (course_id, ip_hash) "
        "WHERE user_id IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_reviews_course ON course_reviews (course_id, created_at DESC)"
    )

    # ── course_review_reports ─────────────────────────────────────────────────
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

    # ── course_cache ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE course_cache (
            cache_key   VARCHAR(64) PRIMARY KEY,
            result      JSONB NOT NULL,
            expires_at  TIMESTAMPTZ NOT NULL
        )
    """)

    # ── app_config ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE app_config (
            key         VARCHAR(100) PRIMARY KEY,
            value       JSONB NOT NULL,
            updated_at  TIMESTAMPTZ DEFAULT now()
        )
    """)

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE refresh_tokens (
            jti         VARCHAR(64) PRIMARY KEY,
            user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            user_agent  TEXT,
            issued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at  TIMESTAMPTZ NOT NULL,
            revoked_at  TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX idx_rt_user ON refresh_tokens (user_id)")

    # ── updated_at trigger ────────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN NEW.updated_at = now(); RETURN NEW; END;
        $$ LANGUAGE plpgsql
    """)
    for tbl in ("users", "courses", "places", "course_reviews"):
        op.execute(
            f"CREATE TRIGGER trg_{tbl}_updated BEFORE UPDATE ON {tbl} "
            f"FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )

    # ── app_config seed values ────────────────────────────────────────────────
    op.execute("""
        INSERT INTO app_config (key, value) VALUES
            ('cache.ttl_days',                  '"14"'),
            ('ratelimit.user_daily',             '"3"'),
            ('ratelimit.review_ip_daily',        '"20"'),
            ('ratelimit.timezone',               '"Asia/Seoul"'),
            ('rating.prior_mean',                '"50"'),
            ('rating.prior_count',               '"5"'),
            ('freshness.sync_interval_days',     '"30"'),
            ('freshness.stale_days',             '"30"'),
            ('recommend.radius_base_km',         '"5"'),
            ('recommend.radius_expand_km',       '"7"'),
            ('recommend.similar_top_n',          '"3"'),
            ('report.hide_threshold',            '"5"')
    """)


def downgrade() -> None:
    # Triggers
    for tbl in ("users", "courses", "places", "course_reviews"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_updated ON {tbl}")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    # Tables (reverse dependency order)
    for tbl in (
        "app_config",
        "course_cache",
        "refresh_tokens",
        "course_review_reports",
        "course_reviews",
        "recommendation_requests",
        "course_places",
        "places",
        "courses",
        "users",
        "station_lines",
        "stations",
    ):
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")

    # Enum types
    for enum in (
        "report_reason",
        "served_from",
        "theme_tag",
        "companion_type",
        "budget_tier",
        "dating_stage",
        "gender_type",
        "oauth_provider",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum}")
