"use client"

import { useState } from "react"
import { upsertReview } from "@/lib/api"
import styles from "./ReviewForm.module.css"

interface Props {
  courseId: number
  initialScore?: number
  initialComment?: string
  initialLinks?: string[]
  onSuccess: () => void
  onCancel: () => void
}

function scoreColor(score: number): string {
  if (score >= 80) return "#22c55e"
  if (score >= 60) return "#f97316"
  return "#ef4444"
}

export default function ReviewForm({
  courseId,
  initialScore = 50,
  initialComment = "",
  initialLinks = [],
  onSuccess,
  onCancel,
}: Props) {
  const [score, setScore] = useState(initialScore)
  const [comment, setComment] = useState(initialComment)
  const [links, setLinks] = useState<string[]>(initialLinks)
  const [linkInput, setLinkInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addLink = () => {
    const trimmed = linkInput.trim()
    if (!trimmed || links.length >= 3) return
    setLinks((prev) => [...prev, trimmed])
    setLinkInput("")
  }

  const removeLink = (idx: number) => {
    setLinks((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await upsertReview(courseId, {
        score,
        comment: comment.trim() || undefined,
        links,
      })
      onSuccess()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "제출 실패")
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.scoreWrap}>
        <label className={styles.scoreLabel}>
          점수&nbsp;
          <span className={styles.scoreNum} style={{ color: scoreColor(score) }}>
            {score}점
          </span>
        </label>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={score}
          onChange={(e) => setScore(Number(e.target.value))}
          className={styles.slider}
          style={{ "--fill": scoreColor(score) } as React.CSSProperties}
        />
        <div className={styles.scoreHints}>
          <span>0</span><span>50</span><span>100</span>
        </div>
      </div>

      <textarea
        className={styles.textarea}
        placeholder="댓글 (선택, 500자 이내)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        maxLength={500}
        rows={3}
      />

      <div className={styles.linkSection}>
        <div className={styles.linkRow}>
          <input
            type="url"
            className={styles.linkInput}
            placeholder="관련 링크 추가 (선택)"
            value={linkInput}
            onChange={(e) => setLinkInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addLink() } }}
            disabled={links.length >= 3}
          />
          <button
            type="button"
            className={styles.linkAddBtn}
            onClick={addLink}
            disabled={!linkInput.trim() || links.length >= 3}
          >
            추가
          </button>
        </div>
        {links.map((l, i) => (
          <div key={i} className={styles.linkChip}>
            <span className={styles.linkText}>{l}</span>
            <button type="button" onClick={() => removeLink(i)} className={styles.linkDel}>×</button>
          </div>
        ))}
      </div>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.actions}>
        <button type="button" className={styles.cancelBtn} onClick={onCancel} disabled={loading}>
          취소
        </button>
        <button type="submit" className={styles.submitBtn} disabled={loading}>
          {loading ? "저장 중..." : "리뷰 등록"}
        </button>
      </div>
    </form>
  )
}
