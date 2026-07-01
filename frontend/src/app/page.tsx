"use client"

import { FormEvent, useState } from "react"
import { useRouter } from "next/navigation"
import styles from "./page.module.css"
import LoginButton from "@/components/LoginButton"
import LoginGateModal from "@/components/LoginGateModal"
import QuotaBadge, { getRemainingCount } from "@/components/QuotaBadge"
import { useDynamicPlaceholder } from "@/hooks/useDynamicPlaceholder"
import { getAccessToken, isLoggedIn } from "@/lib/auth"

export default function Home() {
  const router = useRouter()
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [showLoginGate, setShowLoginGate] = useState(false)

  const placeholder = useDynamicPlaceholder(query.length > 0)

  const isExhausted = isLoggedIn() && getRemainingCount() === 0
  const canSubmit = query.trim().length > 0 && !loading && !isExhausted

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

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
            어떻게 놀고 싶은지 한 문장만 알려주면 AI가 위치까지 파악해서 딱 맞는 코스를 짜드려요
          </p>
        </header>

        <QuotaBadge />

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
            />
          </div>

          <button
            className={`${styles.button} ${loading ? styles.buttonLoading : ""}`}
            type="submit"
            disabled={!canSubmit}
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
