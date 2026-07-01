import styles from "./page.module.css"
import ReviewSection from "@/components/ReviewSection"
import PlaceReportButton from "@/components/PlaceReportButton"
import { THEME_TAG_KO, BUDGET_TIER_KO, COMPANION_TYPE_KO } from "@/lib/enumOptions"

const API_URL =
  process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://backend:8080"

interface PlaceOption {
  place_id: number
  name: string
  category: string | null
  address: string | null
  description: string
  walking_distance_from_station_km: number | null
  status: string | null
}

interface Stage {
  stage_order: number
  stage_label: string
  options: PlaceOption[]
}

interface CourseDetail {
  course_id: number
  station_name: string | null
  theme_tags: string[]
  budget_tier: string | null
  companion_type: string | null
  stages: Stage[]
  bayesian_score: number
  avg_score: number | null
  rating_count: number
  is_stale: boolean
  has_closed: boolean
  og: { title: string; description: string; image_url: string | null }
}

async function getCourse(id: string): Promise<CourseDetail | null> {
  try {
    const res = await fetch(`${API_URL}/v1/courses/${id}`, { cache: "no-store" })
    if (!res.ok) return null
    const json = await res.json()
    return json.data as CourseDetail
  } catch {
    return null
  }
}

export default async function CourseDetailPage({
  params,
}: {
  params: Promise<{ course_id: string }>
}) {
  const { course_id } = await params
  const course = await getCourse(course_id)

  if (!course) {
    return (
      <div className={styles.centered}>
        <p>코스를 찾을 수 없어요.</p>
        <a href="/courses" className={styles.back}>← 코스 탐색으로</a>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.topBar}>
        <a href="/courses" className={styles.back}>← 코스 탐색</a>
        <span className={styles.scoreBadge}>★ {course.bayesian_score.toFixed(1)}</span>
      </div>

      <header className={styles.header}>
        {course.station_name && (
          <span className={styles.station}>{course.station_name}역</span>
        )}
        <h1 className={styles.title}>{course.og.title}</h1>
        <p className={styles.desc}>{course.og.description}</p>

        <div className={styles.meta}>
          {course.theme_tags.map((t) => (
            <span key={t} className={styles.tag}>{THEME_TAG_KO[t] ?? t}</span>
          ))}
          {course.budget_tier && (
            <span className={styles.tag}>{BUDGET_TIER_KO[course.budget_tier] ?? course.budget_tier}</span>
          )}
          {course.companion_type && (
            <span className={styles.tag}>{COMPANION_TYPE_KO[course.companion_type] ?? course.companion_type}</span>
          )}
        </div>

        {(course.is_stale || course.has_closed) && (
          <p className={styles.warning}>
            {course.has_closed ? "⚠ 폐업한 장소가 포함되어 있어요." : "⚠ 정보가 오래됐을 수 있어요."}
          </p>
        )}
      </header>

      <div className={styles.stages}>
        {course.stages.map((stage) => (
          <section key={stage.stage_order} className={styles.stageSection}>
            <h2 className={styles.stageHeader}>
              {stage.stage_order}단계 · {stage.stage_label}
              {stage.options.length > 1 && <span className={styles.pickOne}>택1</span>}
            </h2>
            <ol className={styles.places}>
              {stage.options.map((p) => (
                <li key={p.place_id} className={styles.placeItem}>
                  <div className={styles.placeBody}>
                    <div className={styles.placeName}>{p.name}</div>
                    {p.category && <div className={styles.placeMeta}>{p.category}</div>}
                    {p.address && <div className={styles.placeMeta}>{p.address}</div>}
                    {p.description && <p className={styles.placeDesc}>{p.description}</p>}
                    {p.status === "CLOSED" && (
                      <span className={styles.closedBadge}>폐업</span>
                    )}
                    {p.walking_distance_from_station_km != null && (
                      <p className={styles.walk}>🚶 역에서 도보 {p.walking_distance_from_station_km.toFixed(1)} km</p>
                    )}
                    <PlaceReportButton placeId={p.place_id} placeName={p.name} />
                  </div>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>

      <ReviewSection courseId={course.course_id} />
    </div>
  )
}
