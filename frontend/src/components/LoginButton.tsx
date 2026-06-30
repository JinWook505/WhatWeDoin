"use client"

import { useEffect, useState } from "react"
import { clearTokens, getAccessToken, isLoggedIn, logout } from "@/lib/auth"
import styles from "./LoginButton.module.css"

const KAKAO_CLIENT_ID = process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID ?? ""
const KAKAO_REDIRECT_URI = process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI ?? ""

function getKakaoNickname(): string | null {
  if (typeof window === "undefined") return null
  try {
    const token = getAccessToken()
    if (!token) return null
    const payload = JSON.parse(atob(token.split(".")[1]))
    return payload.nickname ?? null
  } catch {
    return null
  }
}

export default function LoginButton() {
  const [loggedIn, setLoggedIn] = useState(false)
  const [nickname, setNickname] = useState<string | null>(null)

  useEffect(() => {
    setLoggedIn(isLoggedIn())
    setNickname(getKakaoNickname())
  }, [])

  function handleLogin() {
    const params = new URLSearchParams({
      client_id: KAKAO_CLIENT_ID,
      redirect_uri: KAKAO_REDIRECT_URI,
      response_type: "code",
    })
    window.location.href = `https://kauth.kakao.com/oauth/authorize?${params}`
  }

  async function handleLogout() {
    await logout()
    clearTokens()
    setLoggedIn(false)
    setNickname(null)
  }

  if (loggedIn) {
    return (
      <div className={styles.userRow}>
        {nickname && <span className={styles.nickname}>{nickname}</span>}
        <button className={styles.logoutBtn} onClick={handleLogout}>
          로그아웃
        </button>
      </div>
    )
  }

  return (
    <button className={styles.kakaoBtn} onClick={handleLogin}>
      <KakaoIcon />
      카카오로 시작
    </button>
  )
}

function KakaoIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path
        d="M9 1.5C4.858 1.5 1.5 4.134 1.5 7.38c0 2.076 1.38 3.9 3.456 4.944l-.882 3.294a.225.225 0 0 0 .336.246L8.4 13.47A8.9 8.9 0 0 0 9 13.5c4.142 0 7.5-2.634 7.5-5.88S13.142 1.5 9 1.5z"
        fill="#000000"
      />
    </svg>
  )
}
