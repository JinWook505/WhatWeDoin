-- WhatWeDoin — 초기 스키마 (PRD 6.2장)
-- 로컬 개발용: docker-entrypoint-initdb.d에 마운트되어 컨테이너 최초 기동 시 실행됨.
-- 스키마 변경 시: init.sql 수정 후 `docker compose down -v && docker compose up -d`

-- ============================================================
-- Extension
-- ============================================================
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- ENUM 타입
-- ============================================================
CREATE TYPE oauth_provider AS ENUM ('KAKAO', 'NAVER');
CREATE TYPE gender_type    AS ENUM ('MALE', 'FEMALE', 'OTHER', 'UNKNOWN');
CREATE TYPE dating_stage   AS ENUM ('SOME', 'EARLY', 'LONGTERM', 'UNKNOWN');
CREATE TYPE budget_tier    AS ENUM ('UNDER_30000', '30000_70000', '70000_150000', 'OVER_150000');
CREATE TYPE companion_type AS ENUM ('SOLO', 'FRIEND', 'COUPLE', 'FAMILY');
CREATE TYPE served_from    AS ENUM ('LLM', 'CACHE');
CREATE TYPE report_reason  AS ENUM ('SPAM', 'INAPPROPRIATE', 'WRONG_INFO', 'OTHER');

CREATE TYPE theme_tag AS ENUM (
  'FOOD',
  'CAFE',
  'BAR',
  'BOARD_GAME',
  'KARAOKE',
  'ARCADE',
  'PARK',
  'CULTURE',
  'SHOPPING',
  'NIGHT_VIEW',
  'MOVIE',
  'ACTIVITY'
);

-- ============================================================
-- 6.2.3 stations — 지하철역 마스터
-- ============================================================
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
);
CREATE INDEX idx_stations_geom ON stations USING GIST (geom);

CREATE TABLE station_lines (
    station_id  BIGINT REFERENCES stations(station_id),
    line_no     VARCHAR(20) NOT NULL,
    PRIMARY KEY (station_id, line_no)
);

-- ============================================================
-- 6.2.1 users
-- ============================================================
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
    withdrawn_at             TIMESTAMPTZ,
    UNIQUE (oauth_provider, oauth_id)
);

-- ============================================================
-- 6.2.4 courses — 코스 (생성 즉시 공개)
-- ============================================================
CREATE TABLE courses (
    course_id                BIGSERIAL PRIMARY KEY,
    station_id               BIGINT NOT NULL REFERENCES stations(station_id),
    theme_tags               theme_tag[] NOT NULL DEFAULT '{}',
    budget_tier              budget_tier NOT NULL,
    companion_type           companion_type NOT NULL,
    head_count               SMALLINT,
    query_text               TEXT,
    places                   JSONB NOT NULL,
    total_walking_distance_km NUMERIC(4,1),
    rating_count             INTEGER DEFAULT 0,
    rating_sum               INTEGER DEFAULT 0,
    bayesian_score           NUMERIC(5,2) DEFAULT 0,
    content_hash             VARCHAR(64) UNIQUE,
    created_at               TIMESTAMPTZ DEFAULT now(),
    updated_at               TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_courses_station ON courses (station_id);
CREATE INDEX idx_courses_theme   ON courses USING GIN (theme_tags);
CREATE INDEX idx_courses_rank    ON courses (station_id, bayesian_score DESC);
CREATE INDEX idx_courses_filter  ON courses (budget_tier, companion_type, head_count);

-- ============================================================
-- 6.2.5 recommendation_requests — 추천 요청 로그
-- ============================================================
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
);
CREATE UNIQUE INDEX uq_rec_idem ON recommendation_requests (user_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE INDEX idx_rec_recent ON recommendation_requests (user_id, created_at DESC);

-- ============================================================
-- 6.2.6 course_reviews — 코스 리뷰
-- ============================================================
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
    CONSTRAINT chk_review_score    CHECK (score BETWEEN 0 AND 100 AND score % 5 = 0)
);
CREATE UNIQUE INDEX uq_review_user ON course_reviews (course_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX uq_review_ip   ON course_reviews (course_id, ip_hash) WHERE user_id IS NULL;
CREATE INDEX idx_reviews_course    ON course_reviews (course_id, created_at DESC);

-- ============================================================
-- 6.2.6b course_review_reports — 리뷰 신고
-- ============================================================
CREATE TABLE course_review_reports (
    id          BIGSERIAL PRIMARY KEY,
    review_id   BIGINT NOT NULL REFERENCES course_reviews(id) ON DELETE CASCADE,
    user_id     BIGINT REFERENCES users(id),
    ip_hash     VARCHAR(64),
    reason      report_reason NOT NULL,
    comment     TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT chk_reporter CHECK (user_id IS NOT NULL OR ip_hash IS NOT NULL)
);
CREATE UNIQUE INDEX uq_report_user ON course_review_reports (review_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX uq_report_ip   ON course_review_reports (review_id, ip_hash) WHERE user_id IS NULL;

-- ============================================================
-- 6.2.7 course_cache
-- ============================================================
CREATE TABLE course_cache (
    cache_key   VARCHAR(64) PRIMARY KEY,
    result      JSONB NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL
);

-- ============================================================
-- 6.2.8 app_config — 운영 설정
-- ============================================================
CREATE TABLE app_config (
    key         VARCHAR(100) PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT now()
);

INSERT INTO app_config (key, value) VALUES
    ('cache.ttl_days',               '"14"'),
    ('ratelimit.user_daily',         '"3"'),
    ('ratelimit.review_ip_daily',    '"20"'),
    ('ratelimit.timezone',           '"Asia/Seoul"'),
    ('rating.prior_mean',            '"50"'),
    ('rating.prior_count',           '"5"'),
    ('freshness.sync_interval_days', '"30"'),
    ('freshness.stale_days',         '"30"'),
    ('recommend.radius_base_km',     '"5"'),
    ('recommend.radius_expand_km',   '"7"'),
    ('recommend.similar_top_n',      '"3"'),
    ('report.hide_threshold',        '"5"');

-- ============================================================
-- 6.2.9 places — 장소 마스터
-- ============================================================
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
);
CREATE INDEX idx_places_geom     ON places USING GIST (geom);
CREATE INDEX idx_places_category ON places (category);

-- ============================================================
-- 6.2.10 course_places — 코스 구성 장소 (동선 순서)
-- ============================================================
CREATE TABLE course_places (
    course_id                   BIGINT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    visit_order                 SMALLINT NOT NULL,
    place_id                    BIGINT NOT NULL REFERENCES places(place_id),
    description                 TEXT,
    walking_distance_to_next_km NUMERIC(4,1),
    created_at                  TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (course_id, visit_order)
);
CREATE INDEX idx_course_places_place ON course_places (place_id);

-- ============================================================
-- 6.2.11 refresh_tokens
-- ============================================================
CREATE TABLE refresh_tokens (
    jti         VARCHAR(64) PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_agent  TEXT,
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ
);
CREATE INDEX idx_rt_user ON refresh_tokens (user_id);

-- ============================================================
-- updated_at 자동 갱신 트리거
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_courses_updated
    BEFORE UPDATE ON courses
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_reviews_updated
    BEFORE UPDATE ON course_reviews
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_places_updated
    BEFORE UPDATE ON places
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
