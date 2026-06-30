"use client"

import { useEffect, useRef, useState } from "react"

const PLACEHOLDERS = [
  "예: 친구들이랑 홍대에서 놀고 싶어. 예산 15000원",
  "예: 혼자 성수동에서 조용히 카페 투어하고 싶어",
  "예: 커플이랑 이태원에서 저녁 먹고 야경 보고 싶어",
  "예: 가족이랑 여의도에서 나들이하고 싶은데 애 데리고 다닐 만한 곳",
  "예: 친구랑 합정역에서 낮에 놀다가 저녁엔 술 한잔하고 싶어",
  "예: 혼자 강남역에서 점심 먹고 카페 작업하고 싶어",
]

export function useDynamicPlaceholder(paused = false): string {
  const [index, setIndex] = useState(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (paused) return
    timerRef.current = setTimeout(() => {
      setIndex((i) => (i + 1) % PLACEHOLDERS.length)
    }, 2500)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [index, paused])

  return PLACEHOLDERS[index]
}
