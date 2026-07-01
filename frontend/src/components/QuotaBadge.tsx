"use client"

import { useEffect, useState } from "react"
import { isLoggedIn, onAuthChange } from "@/lib/auth"
import { getRemainingCount } from "@/lib/quota"
import styles from "./QuotaBadge.module.css"

interface QuotaBadgeProps {
  remaining?: number | null
}

export default function QuotaBadge({ remaining: overrideRemaining }: QuotaBadgeProps = {}) {
  const [remaining, setRemaining] = useState<number | null>(null)
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    const sync = () => {
      setLoggedIn(isLoggedIn())
      if (overrideRemaining != null) {
        setRemaining(overrideRemaining)
      } else {
        setRemaining(getRemainingCount())
      }
    }
    sync()
    return onAuthChange(sync)
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
