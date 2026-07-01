"use client"

import { CourseListItem } from "@/lib/api"
import styles from "./ErrorFallback.module.css"

interface LlmUnavailableProps {
  type: "LLM_UNAVAILABLE"
  query: string
  popularCourses: CourseListItem[]
}

interface UpstreamUnavailableProps {
  type: "UPSTREAM_UNAVAILABLE"
  query: string
}

interface GenericErrorProps {
  type: "GENERIC"
  query: string
  message?: string
}

type ErrorFallbackProps = LlmUnavailableProps | UpstreamUnavailableProps | GenericErrorProps

export default function ErrorFallback(props: ErrorFallbackProps) {
  const retryUrl = `?q=${encodeURIComponent(props.query)}`

  if (props.type === "LLM_UNAVAILABLE") {
    return (
      <div className={styles.container}>
        <div className={styles.icon}>🤖</div>
        <h2 className={styles.title}>AI가 잠시 쉬고 있어요</h2>
        <p className={styles.sub}>
          지금은 추천을 생성할 수 없어요. 잠시 후 다시 시도해 주세요.
        </p>
        <a href={retryUrl} className={styles.retryBtn}>다시 시도하기</a>

        {props.popularCourses.length > 0 && (
          <section className={styles.popular}>
            <p className={styles.popularLabel}>그동안 인기 코스를 둘러보세요</p>
            <ul className={styles.popularList}>
              {props.popularCourses.map((c) => (
                <li key={c.course_id} className={styles.popularItem}>
                  <a href={`/courses/${c.course_id}`} className={styles.popularLink}>
                    <span className={styles.popularTitle}>{c.station_name ? `[${c.station_name}]` : ""} {c.theme_tags.slice(0, 2).join(" · ")}</span>
                    {c.preview_places.length > 0 && (
                      <span className={styles.popularPlaces}>{c.preview_places.slice(0, 3).join(" → ")}</span>
                    )}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        )}

        <a href="/" className={styles.homeLink}>← 홈으로</a>
      </div>
    )
  }

  if (props.type === "UPSTREAM_UNAVAILABLE") {
    return (
      <div className={styles.container}>
        <div className={styles.icon}>🔌</div>
        <h2 className={styles.title}>잠깐, 서버가 바빠요</h2>
        <p className={styles.sub}>
          일시적인 문제가 발생했어요. 입력하신 내용은 그대로 유지됩니다.
        </p>
        <div className={styles.queryBadge}>&ldquo;{props.query}&rdquo;</div>
        <a href={retryUrl} className={styles.retryBtn}>다시 시도하기</a>
        <a href="/" className={styles.homeLink}>← 홈으로</a>
      </div>
    )
  }

  // GENERIC
  return (
    <div className={styles.container}>
      <div className={styles.icon}>⚠️</div>
      <h2 className={styles.title}>코스 생성 중 오류가 발생했어요</h2>
      {props.message && <p className={styles.errorDetail}>{props.message}</p>}
      <a href={retryUrl} className={styles.retryBtn}>다시 시도하기</a>
      <a href="/" className={styles.homeLink}>← 홈으로</a>
    </div>
  )
}
