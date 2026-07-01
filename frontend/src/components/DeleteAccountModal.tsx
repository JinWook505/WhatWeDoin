"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { clearTokens, fetchWithAuth } from "@/lib/auth"
import styles from "./DeleteAccountModal.module.css"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080"

interface Props {
  isOpen: boolean
  onClose: () => void
}

export default function DeleteAccountModal({ isOpen, onClose }: Props) {
  const router = useRouter()
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  async function handleDelete() {
    setDeleting(true)
    setError(null)
    try {
      const res = await fetchWithAuth(`${API_URL}/v1/users/me`, { method: "DELETE" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      clearTokens()
      router.replace("/")
    } catch {
      setError("탈퇴 처리 중 오류가 발생했어요. 잠시 후 다시 시도해주세요.")
      setDeleting(false)
    }
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.iconWrap}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
              stroke="#ef4444"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <h2 className={styles.title}>정말 탈퇴하시겠어요?</h2>
        <p className={styles.desc}>
          탈퇴하면 <strong>개인정보가 즉시 파기</strong>되며, 작성한 리뷰는 익명으로 전환됩니다.
          이 작업은 되돌릴 수 없어요.
        </p>

        {error && <p className={styles.error}>{error}</p>}

        <div className={styles.actions}>
          <button className={styles.cancelBtn} onClick={onClose} disabled={deleting}>
            취소
          </button>
          <button className={styles.deleteBtn} onClick={handleDelete} disabled={deleting}>
            {deleting ? (
              <span className={styles.spinnerWrap}>
                <span className={styles.spinner} />
                처리 중...
              </span>
            ) : (
              "탈퇴하기"
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
