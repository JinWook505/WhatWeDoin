"use client"

import { useState, useEffect, useRef, useCallback, Suspense } from "react"
import { useSearchParams, useRouter, usePathname } from "next/navigation"
import { getCourses, type CourseListItem } from "@/lib/api"
import styles from "./page.module.css"

const THEMES = ["데이트", "맛집탐방", "카페투어", "쇼핑", "문화생활", "야경", "액티비티", "힐링"]
const COMPANIONS = [
  { label: "전체", value: "" },
  { label: "연인", value: "COUPLE" },
  { label: "친구", value: "FRIEND" },
  { label: "가족", value: "FAMILY" },
  { label: "혼자", value: "SOLO" },
]
const BUDGETS = [
  { label: "전체", value: "" },
  { label: "알뜰", value: "BUDGET" },
  { label: "보통", value: "MODERATE" },
  { label: "프리미엄", value: "PREMIUM" },
]
const COMPANION_KO: Record<string, string> = { COUPLE: "연인", FRIEND: "친구", FAMILY: "가족", SOLO: "혼자" }
const BUDGET_KO: Record<string, string> = { BUDGET: "알뜰", MODERATE: "보통", PREMIUM: "프리미엄" }

function FilterBadge({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      className={`${styles.badge} ${active ? styles.badgeActive : ""}`}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

function CourseCard({ course }: { course: CourseListItem }) {
  return (
    <a href={`/courses/${course.course_id}`} className={styles.card}>
      <div className={styles.cardTop}>
        <span className={styles.score}>★ {course.bayesian_score.toFixed(1)}</span>
        <span className={styles.reviewCount}>{course.rating_count}리뷰</span>
        {course.companion_type && (
          <span className={styles.companionBadge}>
            {COMPANION_KO[course.companion_type] ?? course.companion_type}
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
          <span key={t} className={styles.themeTag}>{t}</span>
        ))}
        {course.budget_tier && (
          <span className={styles.budgetTag}>
            {BUDGET_KO[course.budget_tier] ?? course.budget_tier}
          </span>
        )}
      </div>
    </a>
  )
}

function CoursesPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()

  const themes = searchParams.getAll("theme")
  const companion = searchParams.get("companion") ?? ""
  const budget = searchParams.get("budget") ?? ""
  const sort = (searchParams.get("sort") ?? "score") as "score" | "recent"

  const [courses, setCourses] = useState<CourseListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [empty, setEmpty] = useState(false)

  const filtersRef = useRef({ themes, companion, budget, sort })
  const nextCursorRef = useRef<string | null>(null)
  const isLoadingRef = useRef(false)
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  const loadCourses = useCallback(async (reset: boolean) => {
    if (isLoadingRef.current) return
    isLoadingRef.current = true
    setLoading(true)

    const { themes: t, companion: comp, budget: bud, sort: s } = filtersRef.current
    try {
      const data = await getCourses({
        theme: t.length ? t : undefined,
        companion_type: comp || undefined,
        budget_tier: bud || undefined,
        sort: s,
        limit: 20,
        cursor: reset ? undefined : (nextCursorRef.current ?? undefined),
      })
      nextCursorRef.current = data.next_cursor
      const hasNext = !!data.next_cursor
      setHasMore(hasNext)
      if (reset) {
        setCourses(data.courses)
        setEmpty(data.courses.length === 0)
      } else {
        setCourses((prev) => [...prev, ...data.courses])
      }
    } catch {
      setHasMore(false)
    } finally {
      isLoadingRef.current = false
      setLoading(false)
    }
  }, [])

  // Sync filter ref and reload on filter change
  const filtersKey = [themes.join("|"), companion, budget, sort].join(":")
  useEffect(() => {
    filtersRef.current = { themes, companion, budget, sort }
    nextCursorRef.current = null
    setCourses([])
    setHasMore(false)
    setEmpty(false)
    loadCourses(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey, loadCourses])

  // IntersectionObserver for infinite scroll
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

  const updateFilter = (key: string, value: string | string[]) => {
    const params = new URLSearchParams(searchParams.toString())
    if (Array.isArray(value)) {
      params.delete(key)
      for (const v of value) if (v) params.append(key, v)
    } else {
      if (value) params.set(key, value)
      else params.delete(key)
    }
    router.push(`${pathname}?${params.toString()}`)
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <a href="/" className={styles.back}>← 홈</a>
        <h1 className={styles.title}>코스 탐색</h1>
      </header>

      <section className={styles.filters}>
        <div className={styles.filterRow}>
          <span className={styles.filterLabel}>테마</span>
          <div className={styles.badgeRow}>
            {THEMES.map((t) => (
              <FilterBadge
                key={t}
                active={themes.includes(t)}
                onClick={() => {
                  const next = themes.includes(t)
                    ? themes.filter((x) => x !== t)
                    : [...themes, t]
                  updateFilter("theme", next)
                }}
              >
                {t}
              </FilterBadge>
            ))}
          </div>
        </div>

        <div className={styles.filterRow}>
          <span className={styles.filterLabel}>동행</span>
          <div className={styles.badgeRow}>
            {COMPANIONS.map((o) => (
              <FilterBadge
                key={o.value}
                active={companion === o.value}
                onClick={() => updateFilter("companion", o.value)}
              >
                {o.label}
              </FilterBadge>
            ))}
          </div>
        </div>

        <div className={styles.filterRow}>
          <span className={styles.filterLabel}>예산</span>
          <div className={styles.badgeRow}>
            {BUDGETS.map((o) => (
              <FilterBadge
                key={o.value}
                active={budget === o.value}
                onClick={() => updateFilter("budget", o.value)}
              >
                {o.label}
              </FilterBadge>
            ))}
          </div>
        </div>

        <div className={styles.filterRow}>
          <span className={styles.filterLabel}>정렬</span>
          <div className={styles.badgeRow}>
            <FilterBadge active={sort === "score"} onClick={() => updateFilter("sort", "score")}>
              인기순
            </FilterBadge>
            <FilterBadge active={sort === "recent"} onClick={() => updateFilter("sort", "recent")}>
              최신순
            </FilterBadge>
          </div>
        </div>
      </section>

      {loading && courses.length === 0 && (
        <div className={styles.emptyState}>불러오는 중...</div>
      )}
      {empty && !loading && (
        <div className={styles.emptyState}>조건에 맞는 코스가 없어요 🔍</div>
      )}

      {courses.length > 0 && (
        <div className={styles.grid}>
          {courses.map((c) => (
            <CourseCard key={c.course_id} course={c} />
          ))}
        </div>
      )}

      <div ref={sentinelRef} className={styles.sentinel} />
      {loading && courses.length > 0 && (
        <p className={styles.loadingMore}>더 불러오는 중...</p>
      )}
    </div>
  )
}

export default function CoursesPage() {
  return (
    <Suspense
      fallback={
        <div style={{ padding: "40px", color: "var(--foreground-muted)", textAlign: "center" }}>
          불러오는 중...
        </div>
      }
    >
      <CoursesPageContent />
    </Suspense>
  )
}
