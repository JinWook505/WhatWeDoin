"use client"

import { FormEvent, useState } from "react"
import { useRouter } from "next/navigation"
import styles from "./page.module.css"

export default function Home() {
  const router = useRouter()
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading) return
    setLoading(true)
    router.push(`/result?q=${encodeURIComponent(query.trim())}`)
  }

  return (
    <div className={styles.page}>
      <div className={styles.blob1} aria-hidden="true" />
      <div className={styles.blob2} aria-hidden="true" />
      <main className={styles.main}>
        <header className={styles.header}>
          <span className={styles.eyebrow}>AI Course Planner</span>
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
              placeholder={"예: 친구들이랑 학교 끝나고 홍대입구역에서 놀다가\n저녁먹고 집 가고 싶어. 예산은 인당 15000원이야."}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={4}
              autoFocus
            />
          </div>

          <button
            className={styles.button}
            type="submit"
            disabled={!query.trim() || loading}
          >
            {loading ? "코스 생성 중..." : "AI 코스 추천받기"}
          </button>
        </form>
      </main>
    </div>
  )
}
