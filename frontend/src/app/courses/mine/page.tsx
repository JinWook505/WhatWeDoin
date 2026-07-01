"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { getMyCourses, type CourseListItem } from "@/lib/api"
import { isLoggedIn } from "@/lib/auth"
import CourseCard from "@/components/CourseCard"
import styles from "../page.module.css"

export default function MyCoursesPage() {
  const [courses, setCourses] = useState<CourseListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [empty, setEmpty] = useState(false)
  const [unauthorized, setUnauthorized] = useState(false)

  const nextCursorRef = useRef<string | null>(null)
  const isLoadingRef = useRef(false)
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  const loadCourses = useCallback(async (reset: boolean) => {
    if (isLoadingRef.current) return
    isLoadingRef.current = true
    setLoading(true)
    try {
      const data = await getMyCourses({
        limit: 20,
        cursor: reset ? undefined : (nextCursorRef.current ?? undefined),
      })
      nextCursorRef.current = data.next_cursor
      if (reset) {
        setCourses(data.courses)
        setEmpty(data.courses.length === 0)
      } else {
        setCourses((prev) => [...prev, ...data.courses])
      }
    } catch {
      setEmpty(true)
    } finally {
      isLoadingRef.current = false
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isLoggedIn()) {
      setUnauthorized(true)
      setLoading(false)
      return
    }
    loadCourses(true)
  }, [loadCourses])

  useEffect(() => {
    const el = sentinelRef.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isLoadingRef.current && nextCursorRef.current) {
          loadCourses(false)
        }
      },
      { rootMargin: "300px" },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [loadCourses])

  if (unauthorized) {
    return (
      <div className={styles.emptyState}>
        <p>로그인 후 이용할 수 있어요.</p>
        <a href="/" className={styles.back}>← 홈으로</a>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <a href="/courses" className={styles.back}>← 코스 탐색</a>
        <h1 className={styles.title}>내가 만든 코스</h1>
      </header>

      {loading && courses.length === 0 && (
        <div className={styles.emptyState}>불러오는 중...</div>
      )}
      {empty && !loading && (
        <div className={styles.emptyState}>아직 만든 코스가 없어요. 홈에서 첫 코스를 만들어보세요 ✨</div>
      )}

      {courses.length > 0 && (
        <div className={styles.grid}>
          {courses.map((c) => (
            <CourseCard key={c.course_id} course={c} />
          ))}
        </div>
      )}

      <div ref={sentinelRef} className={styles.sentinel} />
    </div>
  )
}
