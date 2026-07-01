"use client"

import { useEffect, useState } from "react"
import { isLoggedIn } from "@/lib/auth"
import styles from "./QuotaBadge.module.css"

const DAILY_LIMIT = 3

function getTodayKey(): string {
  const d = new Date()
  const kst = new Date(d.getTime() + 9 * 60 * 60 * 1000)
  const y = kst.getUTCFullYear()
  const m = String(kst.getUTCMonth() + 1).padStart(2, "0")
  const day = String(kst.getUTCDate()).padStart(2, "0")
  return `wwd_daily_count_${y}${m}${day}`
}

export function getUsedCount(): number {
  if (typeof window === "undefined") return 0
  return parseInt(localStorage.getItem(getTodayKey()) ?? "0", 10)
}

export function incrementUsedCount(): void {
  if (typeof window === "undefined") return
  const key = getTodayKey()
  const current = parseInt(localStorage.getItem(key) ?? "0", 10)
  localStorage.setItem(key, String(current + 1))
}

export function getRemainingCount(): number {
  return Math.max(0, DAILY_LIMIT - getUsedCount())
}

interface QuotaBadgeProps {
  remaining?: number | null
}

export default function QuotaBadge({ remaining: overrideRemaining }: QuotaBadgeProps = {}) {
  const [remaining, setRemaining] = useState<number | null>(null)
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    setLoggedIn(isLoggedIn())
    if (overrideRemaining != null) {
      setRemaining(overrideRemaining)
    } else {
      setRemaining(getRemainingCount())
    }
  }, [overrideRemaining])

  if (!loggedIn) {
    return (
      <p className={styles.hint}>
        로그인 후 AI 추천 하루 3회 무료
      </p>
    )
  }

  if (remaining === null) return null

  if (remaining === 0) {
    return (
      <div className={styles.exhausted}>
        <span className={styles.exhaustedIcon}>⏳</span>
        <span>오늘 추천을 모두 사용했어요</span>
        <span className={styles.reset}>KST 자정에 초기화돼요</span>
      </div>
    )
  }

  return (
    <div className={styles.badge}>
      <span className={styles.count}>{remaining}</span>
      <span className={styles.label}>회 남음</span>
    </div>
  )
}
