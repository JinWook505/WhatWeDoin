"use client"

import { FormEvent, useState } from "react"
import { useRouter } from "next/navigation"
import styles from "./page.module.css"
import LoginButton from "@/components/LoginButton"
import LoginGateModal from "@/components/LoginGateModal"
import { useDynamicPlaceholder } from "@/hooks/useDynamicPlaceholder"
import { getAccessToken } from "@/lib/auth"

export default function Home() {
  const router = useRouter()
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [showLoginGate, setShowLoginGate] = useState(false)

  const placeholder = useDynamicPlaceholder(query.length > 0)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading) return

    if (!getAccessToken()) {
      setShowLoginGate(true)
      return
    }

    setLoading(true)
    router.push(`/result?q=${encodeURIComponent(query.trim())}`)
  }

  return (
    <div className={styles.page}>
      <div className={styles.blob1} aria-hidden="true" />
      <div className={styles.blob2} aria-hidden="true" />
      <main className={styles.main}>
        <header className={styles.header}>
          <div className={styles.topBar}>
            <span className={styles.eyebrow}>AI Course Planner</span>
            <LoginButton />
          </div>
          <h1 className={styles.title}>오늘 뭐하고 놀지?</h1>
          <p className={styles.subtitle}>
            지하철역 하나만 알려주면 AI가 딱 맞는 코스를 짜드려요
          </p>
        </header>

        <form className={styles.form} onSubmit={handleSubmit} noValidate>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="query">
              어떻게 놀고 싶어?
            </label>
            <textarea
              id="query"
              className={styles.textarea}
              placeholder={placeholder}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={4}
              autoFocus
            />
          </div>

          <button
            className={`${styles.button} ${loading ? styles.buttonLoading : ""}`}
            type="submit"
            disabled={!query.trim() || loading}
          >
            {loading ? (
              <>
                <svg
                  className={styles.spinner}
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  aria-hidden="true"
                >
                  <circle cx="8" cy="8" r="6" stroke="currentColor" strokeOpacity="0.3" strokeWidth="2" />
                  <path d="M8 2a6 6 0 0 1 6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                코스 생성 중...
              </>
            ) : "AI 코스 추천받기"}
          </button>
          <a href="/courses" className={styles.exploreLink}>
            코스 탐색하기 →
          </a>
        </form>
      </main>

      {showLoginGate && <LoginGateModal onClose={() => setShowLoginGate(false)} />}
    </div>
  )
}
