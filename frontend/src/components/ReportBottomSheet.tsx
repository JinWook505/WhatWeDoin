"use client"

import { FormEvent, useState } from "react"
import { reportPlace } from "@/lib/api"
import styles from "./ReportBottomSheet.module.css"

interface Props {
  placeId: number
  placeName: string
  onClose: () => void
  onSuccess: (rating?: number) => void
}

const STAR_VALUES = [1, 2, 3, 4, 5] as const

export default function ReportBottomSheet({ placeId, placeName, onClose, onSuccess }: Props) {
  const [rating, setRating] = useState<number | null>(null)
  const [businessHours, setBusinessHours] = useState("")
  const [priceRange, setPriceRange] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!rating && !businessHours && !priceRange) {
      setError("제보할 내용을 하나 이상 입력해주세요.")
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await reportPlace(placeId, {
        rating: rating ?? undefined,
        business_hours_text: businessHours || undefined,
        price_range: priceRange || undefined,
      })
      onSuccess(rating ?? undefined)
    } catch (err) {
      setError(err instanceof Error ? err.message : "제보 실패. 다시 시도해주세요.")
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className={styles.backdrop} onClick={onClose} />
      <div className={styles.sheet}>
        <div className={styles.handle} />
        <div className={styles.content}>
          <div className={styles.sheetHeader}>
            <h2 className={styles.sheetTitle}>제보하기</h2>
            <p className={styles.sheetSub}>{placeName}</p>
          </div>

          <form onSubmit={handleSubmit} className={styles.form}>
            <div className={styles.section}>
              <p className={styles.sectionLabel}>별점</p>
              <div className={styles.stars}>
                {STAR_VALUES.map((v) => (
                  <button
                    key={v}
                    type="button"
                    className={`${styles.star} ${rating != null && v <= rating ? styles.starActive : ""}`}
                    onClick={() => setRating(v === rating ? null : v)}
                    aria-label={`${v}점`}
                  >
                    ★
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.section}>
              <label className={styles.sectionLabel} htmlFor="bh">
                영업시간
              </label>
              <input
                id="bh"
                className={styles.input}
                type="text"
                placeholder="예: 월~금 11:00-22:00, 주말 휴무"
                value={businessHours}
                onChange={(e) => setBusinessHours(e.target.value)}
              />
            </div>

            <div className={styles.section}>
              <label className={styles.sectionLabel} htmlFor="pr">
                가격대
              </label>
              <input
                id="pr"
                className={styles.input}
                type="text"
                placeholder="예: 1인 15,000원~20,000원"
                value={priceRange}
                onChange={(e) => setPriceRange(e.target.value)}
              />
            </div>

            {error && <p className={styles.error}>{error}</p>}

            <div className={styles.btnRow}>
              <button
                type="button"
                className={styles.cancelBtn}
                onClick={onClose}
                disabled={submitting}
              >
                취소
              </button>
              <button
                type="submit"
                className={styles.submitBtn}
                disabled={submitting}
              >
                {submitting ? "제출 중…" : "제보 제출"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
