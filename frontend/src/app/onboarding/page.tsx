"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { fetchWithAuth } from "@/lib/auth"
import styles from "./page.module.css"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080"

const THEMES = ["데이트", "맛집", "카페", "야경", "힐링", "쇼핑", "문화", "액티비티"]
const COMPANIONS = [
  { value: "COUPLE", label: "연인" },
  { value: "FRIEND", label: "친구" },
  { value: "FAMILY", label: "가족" },
  { value: "SOLO", label: "혼자" },
]
const BUDGETS = [
  { value: "BUDGET", label: "저렴하게 (인당 ~1만원)" },
  { value: "MODERATE", label: "적당하게 (인당 1~3만원)" },
  { value: "PREMIUM", label: "여유롭게 (인당 3만원+)" },
]

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState<1 | 2>(1)

  // Step 1 — Terms
  const [termsRequired, setTermsRequired] = useState(false)
  const [privacyRequired, setPrivacyRequired] = useState(false)
  const [marketingOptional, setMarketingOptional] = useState(false)

  // Step 2 — Personalization
  const [companion, setCompanion] = useState("")
  const [selectedThemes, setSelectedThemes] = useState<string[]>([])
  const [budget, setBudget] = useState("")
  const [saving, setSaving] = useState(false)

  const allRequired = termsRequired && privacyRequired
  const allChecked = allRequired && marketingOptional

  function toggleAll(checked: boolean) {
    setTermsRequired(checked)
    setPrivacyRequired(checked)
    setMarketingOptional(checked)
  }

  function toggleTheme(t: string) {
    setSelectedThemes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t].slice(0, 5),
    )
  }

  async function handleSaveAndFinish() {
    setSaving(true)
    try {
      if (companion || selectedThemes.length > 0 || budget) {
        await fetchWithAuth(`${API_URL}/v1/users/me`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            preferred_themes: selectedThemes,
            preferred_companion: companion || null,
            preferred_budget_tier: budget || null,
          }),
        })
      }
    } catch {
      // non-critical — proceed anyway
    }
    localStorage.setItem("wwd_agreed", "1")
    router.replace("/")
  }

  function handleSkip() {
    localStorage.setItem("wwd_agreed", "1")
    router.replace("/")
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        {/* Progress indicator */}
        <div className={styles.progress}>
          <div className={`${styles.dot} ${step >= 1 ? styles.dotActive : ""}`} />
          <div className={styles.line} />
          <div className={`${styles.dot} ${step >= 2 ? styles.dotActive : ""}`} />
        </div>

        {step === 1 && (
          <>
            <h1 className={styles.title}>시작하기 전에</h1>
            <p className={styles.subtitle}>서비스 이용에 필요한 동의를 해주세요</p>

            <div className={styles.checkGroup}>
              <label className={`${styles.checkRow} ${styles.checkAll}`}>
                <input
                  type="checkbox"
                  checked={allChecked}
                  onChange={(e) => toggleAll(e.target.checked)}
                />
                <span>전체 동의</span>
              </label>
              <div className={styles.divider} />
              <label className={styles.checkRow}>
                <input
                  type="checkbox"
                  checked={termsRequired}
                  onChange={(e) => setTermsRequired(e.target.checked)}
                />
                <span>
                  <strong>[필수]</strong> 이용약관 동의
                </span>
              </label>
              <label className={styles.checkRow}>
                <input
                  type="checkbox"
                  checked={privacyRequired}
                  onChange={(e) => setPrivacyRequired(e.target.checked)}
                />
                <span>
                  <strong>[필수]</strong> 개인정보처리방침 동의
                </span>
              </label>
              <label className={styles.checkRow}>
                <input
                  type="checkbox"
                  checked={marketingOptional}
                  onChange={(e) => setMarketingOptional(e.target.checked)}
                />
                <span>[선택] 마케팅 정보 수신 동의</span>
              </label>
            </div>

            <button
              className={styles.primaryBtn}
              onClick={() => setStep(2)}
              disabled={!allRequired}
            >
              다음
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <h1 className={styles.title}>취향을 알려주세요</h1>
            <p className={styles.subtitle}>더 딱 맞는 코스를 추천해드릴게요 (건너뛰기 가능)</p>

            <div className={styles.section}>
              <p className={styles.sectionLabel}>주로 누구랑 놀아요?</p>
              <div className={styles.chipRow}>
                {COMPANIONS.map((c) => (
                  <button
                    key={c.value}
                    className={`${styles.chip} ${companion === c.value ? styles.chipActive : ""}`}
                    onClick={() => setCompanion(companion === c.value ? "" : c.value)}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.section}>
              <p className={styles.sectionLabel}>좋아하는 테마 (최대 5개)</p>
              <div className={styles.chipRow}>
                {THEMES.map((t) => (
                  <button
                    key={t}
                    className={`${styles.chip} ${selectedThemes.includes(t) ? styles.chipActive : ""}`}
                    onClick={() => toggleTheme(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.section}>
              <p className={styles.sectionLabel}>선호 예산대</p>
              <div className={styles.radioGroup}>
                {BUDGETS.map((b) => (
                  <label key={b.value} className={styles.radioRow}>
                    <input
                      type="radio"
                      name="budget"
                      value={b.value}
                      checked={budget === b.value}
                      onChange={() => setBudget(b.value)}
                    />
                    <span>{b.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className={styles.actions}>
              <button className={styles.primaryBtn} onClick={handleSaveAndFinish} disabled={saving}>
                {saving ? "저장 중..." : "시작하기"}
              </button>
              <button className={styles.skipBtn} onClick={handleSkip}>
                건너뛰기
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
