"use client"

import { useState } from "react"
import { recommend, isClarificationResult, ApiError, CourseData, StationResult } from "@/lib/api"
import { COMPANION_TYPE_OPTIONS as COMPANION_OPTIONS, BUDGET_TIER_OPTIONS as BUDGET_OPTIONS } from "@/lib/enumOptions"
import StationSearch from "./StationSearch"
import ResultClient from "./ResultClient"
import styles from "./ClarificationStep.module.css"

interface Props {
  query: string
  missingFields: string[]
  partialParsedInput: {
    theme_tags?: string[]
    budget_tier?: string | null
    companion_type?: string | null
    head_count?: number
    station_name?: string
  }
  dailyRemaining?: number | null
}

export default function ClarificationStep({
  query,
  missingFields,
  partialParsedInput,
  dailyRemaining,
}: Props) {
  const [station, setStation] = useState<StationResult | null>(null)
  const [companionType, setCompanionType] = useState<string | null>(
    partialParsedInput.companion_type ?? null,
  )
  const [budgetTier, setBudgetTier] = useState<string | null>(
    partialParsedInput.budget_tier ?? null,
  )
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CourseData | null>(null)
  const [remaining, setRemaining] = useState<number | null>(dailyRemaining ?? null)

  const needsStation = missingFields.includes("station_id")
  const needsCompanion = missingFields.includes("companion_type")
  const needsBudget = missingFields.includes("budget_tier")

  const canSubmit =
    (!needsStation || station != null) &&
    (!needsCompanion || companionType != null) &&
    (!needsBudget || budgetTier != null) &&
    !submitting

  const handleSubmit = async () => {
    if (!canSubmit) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await recommend(query, [], crypto.randomUUID(), {
        stationId: station?.station_id,
        parsedInput: {
          theme_tags: partialParsedInput.theme_tags ?? [],
          budget_tier: budgetTier,
          companion_type: companionType,
          head_count: partialParsedInput.head_count ?? 2,
          station_name: station?.name ?? partialParsedInput.station_name,
        },
      })
      if (isClarificationResult(res)) {
        setError("여전히 정보가 부족해요. 처음 화면에서 다시 시도해주세요.")
        return
      }
      if (res.data) {
        setResult(res.data)
        if (res.daily_remaining != null) setRemaining(res.daily_remaining)
      }
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "추천 생성 실패")
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return <ResultClient initialData={result} query={query} dailyRemaining={remaining} />
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>몇 가지만 더 알려주세요</h1>
      <p className={styles.subtitle}>
        입력하신 내용만으로는 코스를 짜기에 정보가 조금 부족해요.
      </p>

      {needsStation && (
        <div className={styles.field}>
          <label className={styles.label}>어느 역 근처에서?</label>
          <StationSearch selected={station} onSelect={setStation} />
        </div>
      )}

      {needsCompanion && (
        <div className={styles.field}>
          <label className={styles.label}>누구랑 놀아?</label>
          <div className={styles.chips}>
            {COMPANION_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`${styles.chip} ${companionType === opt.value ? styles.chipActive : ""}`}
                onClick={() => setCompanionType(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {needsBudget && (
        <div className={styles.field}>
          <label className={styles.label}>예산은 어느 정도?</label>
          <div className={styles.chips}>
            {BUDGET_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`${styles.chip} ${budgetTier === opt.value ? styles.chipActive : ""}`}
                onClick={() => setBudgetTier(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && <p className={styles.error}>{error}</p>}

      <button className={styles.submitBtn} onClick={handleSubmit} disabled={!canSubmit}>
        {submitting ? "코스 생성 중..." : "코스 만들기"}
      </button>
    </div>
  )
}
