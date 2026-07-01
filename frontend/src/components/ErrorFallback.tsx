"use client"

import styles from "./ErrorFallback.module.css"

interface Props {
  status?: number
  code?: string
  message?: string
  onRetry?: () => void
}

const ERROR_CONFIG: Record<number, { emoji: string; title: string; sub: string; action?: string }> = {
  401: {
    emoji: "🔐",
    title: "로그인이 필요해요",
    sub: "AI 코스 추천은 로그인 후 이용 가능해요.",
    action: "카카오로 로그인",
  },
  429: {
    emoji: "⏳",
    title: "오늘 추천 한도를 모두 사용했어요",
    sub: "KST 자정에 초기화됩니다. 내일 다시 이용해주세요.",
  },
  503: {
    emoji: "🤖",
    title: "AI 서비스가 잠시 바빠요",
    sub: "잠시 후 다시 시도해주세요.",
    action: "다시 시도",
  },
}

export default function ErrorFallback({ status, code, message, onRetry }: Props) {
  const config = status ? ERROR_CONFIG[status] : null
  const emoji = config?.emoji ?? "😢"
  const title = config?.title ?? "오류가 발생했어요"
  const sub = config?.sub ?? (message ?? "잠시 후 다시 시도해주세요.")

  const handleAction = () => {
    if (status === 401) {
      const clientId = process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID
      const redirectUri = process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI
      if (clientId && redirectUri) {
        window.location.href = `https://kauth.kakao.com/oauth/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code`
        return
      }
    }
    onRetry?.()
  }

  const actionLabel = config?.action ?? (onRetry ? "다시 시도" : null)

  return (
    <div className={styles.container}>
      <span className={styles.emoji}>{emoji}</span>
      <p className={styles.title}>{title}</p>
      {code && <p className={styles.code}>{code}</p>}
      <p className={styles.sub}>{sub}</p>
      <div className={styles.actions}>
        {actionLabel && (
          <button className={styles.actionBtn} onClick={handleAction}>
            {actionLabel}
          </button>
        )}
        <a href="/" className={styles.homeLink}>← 홈으로</a>
      </div>
    </div>
  )
}
