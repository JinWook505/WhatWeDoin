"use client"

import { useEffect, useRef, useState } from "react"
import { useSearchParams } from "next/navigation"
import {
  recommend,
  isClarificationResult,
  ApiError,
  CourseData,
  ClarificationResponse,
} from "@/lib/api"
import ResultClient from "./ResultClient"
import ClarificationStep from "./ClarificationStep"
import ErrorFallback from "./ErrorFallback"
import { incrementUsedCount } from "@/lib/quota"
import pageStyles from "@/app/result/page.module.css"
import loadingStyles from "@/app/result/loading.module.css"

interface ErrorState {
  status?: number
  code?: string
  message?: string
}

export default function ResultPageClient() {
  const searchParams = useSearchParams()
  const q = searchParams.get("q")

  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<CourseData | null>(null)
  const [dailyRemaining, setDailyRemaining] = useState<number | null>(null)
  const [clarification, setClarification] = useState<ClarificationResponse | null>(null)
  const [error, setError] = useState<ErrorState | null>(null)
  const idempotencyKeyRef = useRef<{ query: string | null; key: string } | null>(null)

  useEffect(() => {
    if (!q) {
      setLoading(false)
      return
    }
    if (idempotencyKeyRef.current?.query !== q) {
      idempotencyKeyRef.current = { query: q, key: crypto.randomUUID() }
    }
    const idempotencyKey = idempotencyKeyRef.current.key
    let cancelled = false
    setLoading(true)
    recommend(q, [], idempotencyKey)
      .then((res) => {
        if (cancelled) return
        if (isClarificationResult(res)) {
          setClarification(res)
        } else {
          incrementUsedCount()
          setData(res.data)
          setDailyRemaining(res.daily_remaining ?? null)
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        if (err instanceof ApiError) {
          setError({ status: err.status, code: err.code, message: err.message })
        } else {
          setError({ status: 500 })
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [q])

  if (!q) {
    return (
      <div className={pageStyles.centered}>
        <p>검색 정보가 없습니다.</p>
        <a href="/" className={pageStyles.back}>← 홈으로 돌아가기</a>
      </div>
    )
  }

  if (loading) {
    return (
      <div className={loadingStyles.container}>
        <div className={loadingStyles.spinner}>
          <div className={loadingStyles.spinnerRing} />
        </div>
        <h2 className={loadingStyles.title}>AI가 코스를 짜는 중이에요</h2>
        <p className={loadingStyles.sub}>딱 맞는 장소들을 찾고 있어요...</p>
        <div className={loadingStyles.cards}>
          {[1, 2, 3].map((i) => (
            <div key={i} className={loadingStyles.card} />
          ))}
        </div>
      </div>
    )
  }

  if (clarification) {
    return (
      <ClarificationStep
        query={q}
        missingFields={clarification.missing_fields}
        partialParsedInput={clarification.partial_parsed_input}
      />
    )
  }

  if (error || !data) {
    return (
      <ErrorFallback
        status={error?.status}
        code={error?.code}
        message={error?.message}
      />
    )
  }

  return <ResultClient initialData={data} query={q} dailyRemaining={dailyRemaining} />
}
