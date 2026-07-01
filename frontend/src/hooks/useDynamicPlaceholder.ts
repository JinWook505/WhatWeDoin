"use client"

import { useEffect, useState } from "react"
import { getPlaceholder } from "@/lib/api"

const FALLBACK_PLACEHOLDER = "예: 친구들이랑 홍대에서 놀고 싶어. 예산 15000원"

export function useDynamicPlaceholder(paused = false): string {
  const [placeholder, setPlaceholder] = useState(FALLBACK_PLACEHOLDER)

  useEffect(() => {
    if (paused) return
    let cancelled = false
    getPlaceholder()
      .then((res) => {
        if (!cancelled && res.placeholder) setPlaceholder(res.placeholder)
      })
      .catch(() => {
        // keep the static fallback on failure
      })
    return () => {
      cancelled = true
    }
  }, [paused])

  return placeholder
}
