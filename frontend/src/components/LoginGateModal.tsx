"use client"

import styles from "./LoginGateModal.module.css"

interface Props {
  onClose: () => void
}

export default function LoginGateModal({ onClose }: Props) {
  const kakaoClientId = process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID
  const kakaoRedirectUri = process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI

  const handleLogin = () => {
    if (!kakaoClientId || !kakaoRedirectUri) return
    window.location.href = `https://kauth.kakao.com/oauth/authorize?client_id=${kakaoClientId}&redirect_uri=${encodeURIComponent(kakaoRedirectUri)}&response_type=code`
  }

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.close} onClick={onClose} aria-label="닫기">✕</button>
        <p className={styles.icon}>🔑</p>
        <h2 className={styles.title}>로그인이 필요해요</h2>
        <p className={styles.desc}>
          AI 코스 추천은 로그인한 회원만 이용할 수 있어요.
          <br />
          하루 3번 무료로 추천받을 수 있어요!
        </p>
        <button className={styles.kakaoBtn} onClick={handleLogin}>
          카카오로 시작하기
        </button>
      </div>
    </div>
  )
}
