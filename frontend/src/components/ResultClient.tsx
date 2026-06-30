"use client"

import { useState, useCallback } from "react"
import { recommend, CourseData } from "@/lib/api"
import CourseTimeline from "./CourseTimeline"
import styles from "./ResultClient.module.css"

interface Props {
  initialData: CourseData
  query: string
}

export default function ResultClient({ initialData, query }: Props) {
  const [data, setData] = useState<CourseData>(initialData)
  const [excludedIds, setExcludedIds] = useState<Set<number>>(new Set())
  const [regenerating, setRegenerating] = useState(false)
  const [showWarning, setShowWarning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const toggleExclude = useCallback((placeId: number) => {
    setExcludedIds((prev) => {
      const next = new Set(prev)
      if (next.has(placeId)) next.delete(placeId)
      else next.add(placeId)
      return next
    })
  }, [])

  const handleRegenerate = async () => {
    setShowWarning(false)
    setRegenerating(true)
    setError(null)
    try {
      const res = await recommend(query, Array.from(excludedIds))
      if (res.data) {
        setData(res.data)
        setExcludedIds(new Set())
        window.scrollTo({ top: 0, behavior: "smooth" })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "재생성 실패"
      setError(msg)
    } finally {
      setRegenerating(false)
    }
  }

  const hasExclusions = excludedIds.size > 0

  return (
    <>
      <header className={styles.header}>
        <a href="/" className={styles.backLink}>← 다시 검색</a>
        {data.station_name && (
          <span className={styles.station}>{data.station_name} 근처</span>
        )}
        <h1 className={styles.title}>{data.title}</h1>
        {data.description && <p className={styles.desc}>{data.description}</p>}
        {data.total_walking_distance_km != null && (
          <p className={styles.distance}>
            도보 총 {data.total_walking_distance_km.toFixed(1)} km
          </p>
        )}
      </header>

      <CourseTimeline
        places={data.places}
        courseId={data.course_id}
        excludedIds={excludedIds}
        onToggleExclude={toggleExclude}
      />

      {error && <p className={styles.error}>{error}</p>}

      {hasExclusions && (
        <div className={styles.regenBar}>
          <span className={styles.regenHint}>
            {excludedIds.size}개 장소 제외됨
          </span>
          <button
            className={styles.regenBtn}
            onClick={() => setShowWarning(true)}
            disabled={regenerating}
          >
            {regenerating ? "재생성 중..." : "코스 재생성"}
          </button>
        </div>
      )}

      {showWarning && (
        <div className={styles.overlay} onClick={() => setShowWarning(false)}>
          <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
            <p className={styles.dialogTitle}>코스를 재생성할까요?</p>
            <p className={styles.dialogDesc}>
              일일 추천 잔여 횟수가 1회 차감됩니다.
            </p>
            <div className={styles.dialogActions}>
              <button className={styles.cancelBtn} onClick={() => setShowWarning(false)}>
                취소
              </button>
              <button className={styles.confirmBtn} onClick={handleRegenerate}>
                재생성
              </button>
            </div>
          </div>
        </div>
      )}

      {data.similar_top_courses.length > 0 && (
        <section className={styles.similar}>
          <h2 className={styles.similarTitle}>비슷한 인기 코스</h2>
          <ul className={styles.similarList}>
            {data.similar_top_courses.slice(0, 3).map((c) => (
              <li key={c.course_id} className={styles.similarItem}>
                {c.title ?? `코스 #${c.course_id}`}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}
