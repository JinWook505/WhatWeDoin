"use client"

import { useState, useCallback } from "react"
import { recommend, isClarificationResult, CourseData } from "@/lib/api"
import CourseTimeline from "./CourseTimeline"
import CourseMap from "./CourseMap"
import ReviewSection from "./ReviewSection"
import SimilarCourses from "./SimilarCourses"
import { incrementUsedCount } from "@/lib/quota"
import styles from "./ResultClient.module.css"

interface Props {
  initialData: CourseData
  query: string
  dailyRemaining?: number | null
}

export default function ResultClient({ initialData, query, dailyRemaining: initialRemaining }: Props) {
  const [data, setData] = useState<CourseData>(initialData)
  const [excludedIds, setExcludedIds] = useState<Set<number>>(new Set())
  const [regenerating, setRegenerating] = useState(false)
  const [showWarning, setShowWarning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [remaining, setRemaining] = useState<number | null>(initialRemaining ?? null)

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
      const res = await recommend(query, Array.from(excludedIds), crypto.randomUUID())
      if (isClarificationResult(res)) {
        setError("정보가 더 필요해요. 처음 화면에서 다시 입력해주세요.")
        return
      }
      if (res.data) {
        incrementUsedCount()
        setData(res.data)
        setExcludedIds(new Set())
        if (res.daily_remaining != null) setRemaining(res.daily_remaining)
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
        <div className={styles.topBar}>
          <a href="/" className={styles.backLink}>← 다시 검색</a>
          {remaining != null && (
            <span className={styles.remainingBadge}>
              오늘 {remaining}회 남음
            </span>
          )}
        </div>
        {data.station_name && (
          <span className={styles.station}>{data.station_name} 근처</span>
        )}
        <h1 className={styles.title}>{data.title}</h1>
        {data.description && <p className={styles.desc}>{data.description}</p>}
      </header>

      <CourseMap stages={data.stages} excludedIds={excludedIds} />

      {data.total_walking_distance_km != null && (
        <p className={styles.distance}>
          총 도보 이동거리 약 {data.total_walking_distance_km}km
        </p>
      )}

      <CourseTimeline
        stages={data.stages}
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
              {remaining != null
                ? `일일 잔여 횟수 ${remaining}회 중 1회가 차감됩니다.`
                : "일일 추천 잔여 횟수가 1회 차감됩니다."}
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

      <ReviewSection courseId={data.course_id} />

      <SimilarCourses courses={data.similar_top_courses} />
    </>
  )
}
