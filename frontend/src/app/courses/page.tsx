"use client"

import { useState, useEffect, useRef, useCallback, Suspense } from "react"
import { useSearchParams, useRouter, usePathname } from "next/navigation"
import { getCourses, type CourseListItem, type StationResult } from "@/lib/api"
import { THEME_TAG_OPTIONS, COMPANION_TYPE_OPTIONS, BUDGET_TIER_OPTIONS } from "@/lib/enumOptions"
import StationSearch from "@/components/StationSearch"
import CourseCard from "@/components/CourseCard"
import { isLoggedIn } from "@/lib/auth"
import styles from "./page.module.css"

const THEMES = THEME_TAG_OPTIONS
const COMPANIONS = [{ label: "전체", value: "" }, ...COMPANION_TYPE_OPTIONS]
const BUDGETS = [{ label: "전체", value: "" }, ...BUDGET_TIER_OPTIONS]

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

function CoursesPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()

  const themes = searchParams.getAll("theme")
  const companion = searchParams.get("companion") ?? ""
  const budget = searchParams.get("budget") ?? ""
  const sort = (searchParams.get("sort") ?? "score") as "score" | "recent"
  const stationIdParam = searchParams.get("station_id")
  const stationNameParam = searchParams.get("station_name")
  const station: StationResult | null =
    stationIdParam && stationNameParam
      ? { station_id: Number(stationIdParam), name: stationNameParam, lat: 0, lng: 0 }
      : null

  const [courses, setCourses] = useState<CourseListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [empty, setEmpty] = useState(false)
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    setLoggedIn(isLoggedIn())
  }, [])

  const filtersRef = useRef({ themes, companion, budget, sort, stationId: station?.station_id })
  const nextCursorRef = useRef<string | null>(null)
  const isLoadingRef = useRef(false)
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  const loadCourses = useCallback(async (reset: boolean) => {
    if (isLoadingRef.current) return
    isLoadingRef.current = true
    setLoading(true)

    const { themes: t, companion: comp, budget: bud, sort: s, stationId } = filtersRef.current
    try {
      const data = await getCourses({
        theme: t.length ? t : undefined,
        companion_type: comp || undefined,
        budget_tier: bud || undefined,
        station_id: stationId,
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
  const filtersKey = [themes.join("|"), companion, budget, sort, station?.station_id].join(":")
  useEffect(() => {
    filtersRef.current = { themes, companion, budget, sort, stationId: station?.station_id }
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

  const handleStationSelect = (s: StationResult | null) => {
    const params = new URLSearchParams(searchParams.toString())
    if (s) {
      params.set("station_id", String(s.station_id))
      params.set("station_name", s.name)
    } else {
      params.delete("station_id")
      params.delete("station_name")
    }
    router.push(`${pathname}?${params.toString()}`)
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <a href="/" className={styles.back}>← 홈</a>
        <h1 className={styles.title}>코스 탐색</h1>
        {loggedIn && (
          <a href="/courses/mine" className={styles.myCoursesLink}>내 코스 →</a>
        )}
      </header>

      <section className={styles.filters}>
        <div className={styles.filterRow}>
          <span className={styles.filterLabel}>역</span>
          <div className={`${styles.badgeRow} ${styles.stationFilter}`}>
            <StationSearch selected={station} onSelect={handleStationSelect} />
          </div>
        </div>

        <div className={styles.filterRow}>
          <span className={styles.filterLabel}>테마</span>
          <div className={styles.badgeRow}>
            {THEMES.map((t) => (
              <FilterBadge
                key={t.value}
                active={themes.includes(t.value)}
                onClick={() => {
                  const next = themes.includes(t.value)
                    ? themes.filter((x) => x !== t.value)
                    : [...themes, t.value]
                  updateFilter("theme", next)
                }}
              >
                {t.label}
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
