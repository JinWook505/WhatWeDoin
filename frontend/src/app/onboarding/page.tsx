"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { fetchWithAuth } from "@/lib/auth"
import {
  THEME_TAG_OPTIONS as THEMES,
  COMPANION_TYPE_OPTIONS as COMPANIONS,
  BUDGET_TIER_OPTIONS as BUDGETS,
  GENDER_OPTIONS as GENDERS,
  DATING_STAGE_OPTIONS as DATING_STAGES,
} from "@/lib/enumOptions"
import styles from "./page.module.css"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080"

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
  const [gender, setGender] = useState("")
  const [birthYear, setBirthYear] = useState("")
  const [datingStage, setDatingStage] = useState("")
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

  async function persistConsentAndPersonalization(personalize: boolean) {
    const now = new Date().toISOString()
    const body: Record<string, unknown> = {
      terms_agreed_at: now,
      privacy_agreed_at: now,
      marketing_agreed: marketingOptional,
    }
    if (personalize) {
      if (selectedThemes.length > 0) body.preferred_theme_tags = selectedThemes
      if (companion) body.preferred_companion_type = companion
      if (budget) body.preferred_budget = budget
      if (gender) body.gender = gender
      if (birthYear) body.birth_year = Number(birthYear)
      if (companion === "COUPLE" && datingStage) body.dating_stage = datingStage
    }
    try {
      await fetchWithAuth(`${API_URL}/v1/users/me`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
    } catch {
      // non-critical — proceed anyway, user can edit later in 마이페이지
    }
  }

  async function handleSaveAndFinish() {
    setSaving(true)
    await persistConsentAndPersonalization(true)
    localStorage.setItem("wwd_agreed", "1")
    router.replace("/")
  }

  async function handleSkip() {
    await persistConsentAndPersonalization(false)
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
                    key={t.value}
                    className={`${styles.chip} ${selectedThemes.includes(t.value) ? styles.chipActive : ""}`}
                    onClick={() => toggleTheme(t.value)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.section}>
              <p className={styles.sectionLabel}>성별 (선택)</p>
              <div className={styles.chipRow}>
                {GENDERS.map((g) => (
                  <button
                    key={g.value}
                    className={`${styles.chip} ${gender === g.value ? styles.chipActive : ""}`}
                    onClick={() => setGender(gender === g.value ? "" : g.value)}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.section}>
              <p className={styles.sectionLabel}>출생연도 (선택)</p>
              <input
                type="number"
                className={styles.yearInput}
                placeholder="예: 1998"
                value={birthYear}
                onChange={(e) => setBirthYear(e.target.value)}
                min={1900}
                max={new Date().getFullYear()}
              />
            </div>

            {companion === "COUPLE" && (
              <div className={styles.section}>
                <p className={styles.sectionLabel}>연애 단계 (선택)</p>
                <div className={styles.chipRow}>
                  {DATING_STAGES.map((d) => (
                    <button
                      key={d.value}
                      className={`${styles.chip} ${datingStage === d.value ? styles.chipActive : ""}`}
                      onClick={() => setDatingStage(datingStage === d.value ? "" : d.value)}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

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
