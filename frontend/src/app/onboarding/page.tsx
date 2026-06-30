"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { fetchWithAuth } from "@/lib/auth"
import styles from "./page.module.css"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080"

const COMPANIONS = [
  { value: "COUPLE", label: "연인" },
  { value: "FRIEND", label: "친구" },
  { value: "FAMILY", label: "가족" },
  { value: "SOLO", label: "혼자" },
]

const THEMES = [
  { value: "FOOD", label: "맛집탐방" },
  { value: "CAFE", label: "카페투어" },
  { value: "BAR", label: "바/술집" },
  { value: "BOARD_GAME", label: "보드게임" },
  { value: "KARAOKE", label: "노래방" },
  { value: "ARCADE", label: "오락실" },
  { value: "PARK", label: "공원/야외" },
  { value: "CULTURE", label: "문화생활" },
  { value: "SHOPPING", label: "쇼핑" },
  { value: "NIGHT_VIEW", label: "야경" },
  { value: "MOVIE", label: "영화" },
  { value: "ACTIVITY", label: "액티비티" },
]

const BUDGETS = [
  { value: "UNDER_30000", label: "3만원 이하" },
  { value: "30000_70000", label: "3~7만원" },
  { value: "70000_150000", label: "7~15만원" },
  { value: "OVER_150000", label: "15만원 이상" },
]

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Step 1
  const [termsAgreed, setTermsAgreed] = useState(false)
  const [privacyAgreed, setPrivacyAgreed] = useState(false)
  const [marketingAgreed, setMarketingAgreed] = useState(false)

  // Step 2
  const [companion, setCompanion] = useState<string | null>(null)
  const [themes, setThemes] = useState<string[]>([])
  const [budget, setBudget] = useState<string | null>(null)

  const toggleTheme = (val: string) => {
    setThemes((prev) =>
      prev.includes(val)
        ? prev.filter((t) => t !== val)
        : prev.length < 5
          ? [...prev, val]
          : prev,
    )
  }

  const handleStep1 = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchWithAuth(`${API_URL}/v1/users/me`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          terms_agreed_at: new Date().toISOString(),
          privacy_agreed_at: new Date().toISOString(),
          marketing_agreed: marketingAgreed,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setStep(2)
    } catch {
      setError("약관 동의 저장 중 오류가 발생했어요. 다시 시도해 주세요.")
    } finally {
      setLoading(false)
    }
  }

  const handleStep2 = async (skip: boolean) => {
    setLoading(true)
    setError(null)
    try {
      if (!skip) {
        const body: Record<string, unknown> = {}
        if (companion) body.preferred_companion_type = companion
        if (themes.length) body.preferred_theme_tags = themes
        if (budget) body.preferred_budget = budget

        if (Object.keys(body).length > 0) {
          const res = await fetchWithAuth(`${API_URL}/v1/users/me`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          })
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
        }
      }
      router.replace("/")
    } catch {
      router.replace("/")
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.progressTrack}>
        <div className={styles.progressFill} style={{ width: `${(step / 2) * 100}%` }} />
      </div>

      <div className={styles.stepLabel}>Step {step} / 2</div>

      <div className={styles.card}>
        {step === 1 && (
          <>
            <h1 className={styles.title}>서비스 이용 동의</h1>
            <p className={styles.subtitle}>
              WhatWeDoin을 이용하기 위해 아래 약관에 동의해 주세요.
            </p>

            <div className={styles.checkList}>
              <label className={styles.checkRow}>
                <input
                  type="checkbox"
                  checked={termsAgreed}
                  onChange={(e) => setTermsAgreed(e.target.checked)}
                  className={styles.checkbox}
                />
                <span>
                  <strong>[필수]</strong> 이용약관 동의
                </span>
              </label>
              <label className={styles.checkRow}>
                <input
                  type="checkbox"
                  checked={privacyAgreed}
                  onChange={(e) => setPrivacyAgreed(e.target.checked)}
                  className={styles.checkbox}
                />
                <span>
                  <strong>[필수]</strong> 개인정보처리방침 동의
                </span>
              </label>
              <label className={styles.checkRow}>
                <input
                  type="checkbox"
                  checked={marketingAgreed}
                  onChange={(e) => setMarketingAgreed(e.target.checked)}
                  className={styles.checkbox}
                />
                <span>
                  <span className={styles.optional}>[선택]</span> 마케팅 정보 수신 동의
                </span>
              </label>
            </div>

            {error && <p className={styles.error}>{error}</p>}

            <button
              className={styles.button}
              onClick={handleStep1}
              disabled={!termsAgreed || !privacyAgreed || loading}
            >
              {loading ? "처리 중..." : "다음으로"}
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <h1 className={styles.title}>취향을 알려주세요</h1>
            <p className={styles.subtitle}>
              더 정확한 코스 추천을 위해 알려주세요.
              <br />
              나중에 프로필에서 변경할 수 있어요.
            </p>

            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>주로 누구랑 가나요?</h2>
              <div className={styles.chips}>
                {COMPANIONS.map((c) => (
                  <button
                    key={c.value}
                    type="button"
                    className={`${styles.chip} ${companion === c.value ? styles.chipActive : ""}`}
                    onClick={() => setCompanion((prev) => (prev === c.value ? null : c.value))}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </section>

            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>
                선호 테마{" "}
                <span className={styles.hint}>(최대 5개)</span>
              </h2>
              <div className={styles.chips}>
                {THEMES.map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    className={`${styles.chip} ${themes.includes(t.value) ? styles.chipActive : ""}`}
                    onClick={() => toggleTheme(t.value)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </section>

            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>예산대는요?</h2>
              <div className={styles.chips}>
                {BUDGETS.map((b) => (
                  <button
                    key={b.value}
                    type="button"
                    className={`${styles.chip} ${budget === b.value ? styles.chipActive : ""}`}
                    onClick={() => setBudget((prev) => (prev === b.value ? null : b.value))}
                  >
                    {b.label}
                  </button>
                ))}
              </div>
            </section>

            {error && <p className={styles.error}>{error}</p>}

            <div className={styles.actions}>
              <button
                className={styles.button}
                onClick={() => handleStep2(false)}
                disabled={loading}
              >
                {loading ? "저장 중..." : "완료하기"}
              </button>
              <button
                className={styles.skipBtn}
                onClick={() => handleStep2(true)}
                disabled={loading}
              >
                건너뛰기
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
