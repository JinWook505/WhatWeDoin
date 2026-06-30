"use client"

import { Suspense, useEffect, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { setTokens } from "@/lib/auth"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080"
const REDIRECT_URI = process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI ?? ""

function AuthCallbackInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const called = useRef(false)

  useEffect(() => {
    if (called.current) return
    called.current = true

    const code = searchParams.get("code")
    const error = searchParams.get("error")

    if (error || !code) {
      router.replace("/?login_error=1")
      return
    }

    fetch(`${API_URL}/v1/auth/kakao`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, redirect_uri: REDIRECT_URI }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        const { access_token, refresh_token, is_new_user } = data.data ?? {}
        if (!access_token || !refresh_token) throw new Error("no tokens")
        setTokens(access_token, refresh_token)
        router.replace(is_new_user ? "/onboarding" : "/")
      })
      .catch(() => {
        router.replace("/?login_error=1")
      })
  }, [router, searchParams])

  return null
}

const spinner = (
  <div
    style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "var(--background)",
      color: "var(--foreground-muted)",
      fontSize: "15px",
      gap: "12px",
      flexDirection: "column",
    }}
  >
    <div
      style={{
        width: "32px",
        height: "32px",
        border: "3px solid rgba(168,85,247,0.2)",
        borderTopColor: "#a855f7",
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }}
    />
    <span>로그인 처리 중...</span>
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </div>
)

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={spinner}>
      <AuthCallbackInner />
      {spinner}
    </Suspense>
  )
}
