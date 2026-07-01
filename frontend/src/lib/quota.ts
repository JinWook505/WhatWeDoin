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

export function resetUsedCount(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(getTodayKey())
}
