"use client"

import { useEffect, useState } from "react"
import styles from "./ThemeToggle.module.css"
import { applyTheme, type Theme } from "@/lib/theme"

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null)

  useEffect(() => {
    const current = document.documentElement.getAttribute("data-theme")
    setTheme(current === "dark" ? "dark" : "light")
  }, [])

  if (!theme) return null

  const next: Theme = theme === "dark" ? "light" : "dark"

  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={() => {
        applyTheme(next)
        setTheme(next)
      }}
      aria-label={theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환"}
      title={theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환"}
    >
      {theme === "dark" ? (
        <svg className={styles.icon} viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="12" cy="12" r="4.5" stroke="currentColor" strokeWidth="1.8" />
          <path
            d="M12 2.5v2.2M12 19.3v2.2M4.2 4.2l1.6 1.6M18.2 18.2l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.2 19.8l1.6-1.6M18.2 5.8l1.6-1.6"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      ) : (
        <svg className={styles.icon} viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M20.5 14.2A8.5 8.5 0 1 1 9.8 3.5a7 7 0 0 0 10.7 10.7Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </button>
  )
}
