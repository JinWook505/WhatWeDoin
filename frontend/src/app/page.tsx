"use client"

import { FormEvent, useCallback, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { searchStations, StationResult } from "@/lib/api"
import styles from "./page.module.css"

export default function Home() {
  const router = useRouter()
  const [stationQuery, setStationQuery] = useState("")
  const [selectedStation, setSelectedStation] = useState<StationResult | null>(null)
  const [suggestions, setSuggestions] = useState<StationResult[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  const fetchSuggestions = useCallback((q: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!q.trim()) {
      setSuggestions([])
      return
    }
    debounceRef.current = setTimeout(async () => {
      try {
        const results = await searchStations(q)
        setSuggestions(results)
        setShowSuggestions(true)
      } catch {
        setSuggestions([])
      }
    }, 250)
  }, [])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  const handleStationInput = (value: string) => {
    setStationQuery(value)
    setSelectedStation(null)
    fetchSuggestions(value)
  }

  const handleSelectStation = (s: StationResult) => {
    setSelectedStation(s)
    setStationQuery(s.name)
    setSuggestions([])
    setShowSuggestions(false)
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!selectedStation || !query.trim() || loading) return
    setLoading(true)
    router.push(
      `/result?station_id=${selectedStation.station_id}&station_name=${encodeURIComponent(selectedStation.name)}&q=${encodeURIComponent(query.trim())}`,
    )
  }

  const isSubmittable = !!selectedStation && !!query.trim() && !loading

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <header className={styles.header}>
          <h1 className={styles.title}>오늘 뭐하고 놀지?</h1>
          <p className={styles.subtitle}>지하철역 기반 AI 놀거리 코스 추천</p>
        </header>

        <form className={styles.form} onSubmit={handleSubmit} noValidate>
          <div className={styles.field} ref={wrapperRef}>
            <label className={styles.label} htmlFor="station">
              지하철역
            </label>
            <input
              id="station"
              className={styles.input}
              type="text"
              placeholder="예: 홍대입구, 강남, 이태원"
              value={stationQuery}
              onChange={(e) => handleStationInput(e.target.value)}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              autoComplete="off"
            />
            {showSuggestions && suggestions.length > 0 && (
              <ul className={styles.suggestions}>
                {suggestions.map((s) => (
                  <li
                    key={s.station_id}
                    className={styles.suggestion}
                    onMouseDown={() => handleSelectStation(s)}
                  >
                    {s.name}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="query">
              어떻게 놀고 싶으세요?
            </label>
            <textarea
              id="query"
              className={styles.textarea}
              placeholder="예: 여자친구랑 낭만있는 저녁 데이트 코스 추천해줘"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
            />
          </div>

          <button className={styles.button} type="submit" disabled={!isSubmittable}>
            {loading ? "코스 생성 중…" : "AI 코스 추천받기 ✨"}
          </button>
        </form>
      </main>
    </div>
  )
}
