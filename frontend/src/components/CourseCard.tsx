import { type CourseListItem } from "@/lib/api"
import { THEME_TAG_KO, COMPANION_TYPE_KO, BUDGET_TIER_KO } from "@/lib/enumOptions"
import styles from "@/app/courses/page.module.css"

export default function CourseCard({ course }: { course: CourseListItem }) {
  return (
    <a href={`/courses/${course.course_id}`} className={styles.card}>
      <div className={styles.cardTop}>
        <span className={styles.score}>★ {course.bayesian_score.toFixed(1)}</span>
        <span className={styles.reviewCount}>{course.rating_count}리뷰</span>
        {course.companion_type && (
          <span className={styles.companionBadge}>
            {COMPANION_TYPE_KO[course.companion_type] ?? course.companion_type}
          </span>
        )}
      </div>

      <p className={styles.stationName}>{course.station_name ?? "역 미정"}역</p>

      {course.preview_places.length > 0 && (
        <p className={styles.previewPlaces}>
          {course.preview_places.slice(0, 3).join(" → ")}
        </p>
      )}

      <div className={styles.cardTags}>
        {course.theme_tags.slice(0, 3).map((t) => (
          <span key={t} className={styles.themeTag}>{THEME_TAG_KO[t] ?? t}</span>
        ))}
        {course.budget_tier && (
          <span className={styles.budgetTag}>
            {BUDGET_TIER_KO[course.budget_tier] ?? course.budget_tier}
          </span>
        )}
      </div>
    </a>
  )
}
