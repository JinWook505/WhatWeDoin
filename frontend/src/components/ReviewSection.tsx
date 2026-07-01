"use client"

import { useState, useEffect, useCallback } from "react"
import { getReviews, deleteMyReview, ReviewItem, ReviewsResponse } from "@/lib/api"
import ReviewForm from "./ReviewForm"
import styles from "./ReviewSection.module.css"

interface Props {
  courseId: number
}

export default function ReviewSection({ courseId }: Props) {
  const [data, setData] = useState<ReviewsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [myReview, setMyReview] = useState<ReviewItem | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  const fetchReviews = useCallback(async (cursor?: string) => {
    try {
      const res = await getReviews(courseId, cursor)
      if (cursor) {
        setData((prev) =>
          prev
            ? { ...res, reviews: [...prev.reviews, ...res.reviews] }
            : res,
        )
      } else {
        setData(res)
        const mine = res.reviews.find((r) => r.is_mine) ?? null
        setMyReview(mine)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [courseId])

  useEffect(() => { fetchReviews() }, [fetchReviews])

  const handleLoadMore = () => {
    if (!data?.next_cursor || loadingMore) return
    setLoadingMore(true)
    fetchReviews(data.next_cursor)
  }

  const handleFormSuccess = () => {
    setShowForm(false)
    setLoading(true)
    fetchReviews()
  }

  const handleDelete = async () => {
    if (!window.confirm("리뷰를 삭제할까요?")) return
    setDeleteLoading(true)
    try {
      await deleteMyReview(courseId)
      setMyReview(null)
      setLoading(true)
      fetchReviews()
    } catch {
      alert("삭제 실패")
    } finally {
      setDeleteLoading(false)
    }
  }

  if (loading) {
    return <div className={styles.loading}>리뷰 불러오는 중...</div>
  }

  const summary = data?.summary
  const reviews = data?.reviews ?? []

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <h2 className={styles.title}>리뷰</h2>
        {summary && summary.rating_count > 0 && (
          <div className={styles.summary}>
            <span className={styles.bayesian}>★ {summary.bayesian_score.toFixed(1)}</span>
            {summary.avg_score != null && (
              <span className={styles.avg}>평균 {summary.avg_score.toFixed(0)}점</span>
            )}
            <span className={styles.count}>({summary.rating_count}개)</span>
          </div>
        )}
      </div>

      {!showForm && (
        <button
          className={styles.writeBtn}
          onClick={() => setShowForm(true)}
        >
          {myReview ? "리뷰 수정" : "리뷰 쓰기"}
        </button>
      )}

      {showForm && (
        <ReviewForm
          courseId={courseId}
          initialScore={myReview?.score ?? 50}
          initialComment={myReview?.comment ?? ""}
          initialLinks={myReview?.links ?? []}
          onSuccess={handleFormSuccess}
          onCancel={() => setShowForm(false)}
        />
      )}

      <ul className={styles.list}>
        {reviews.map((r) => (
          <li key={r.review_id} className={styles.card}>
            <div className={styles.cardTop}>
              <span className={styles.badge} data-score={r.score}>
                {r.score}점
              </span>
              {r.is_mine && (
                <button
                  className={styles.deleteBtn}
                  onClick={handleDelete}
                  disabled={deleteLoading}
                >
                  삭제
                </button>
              )}
            </div>
            {r.comment && <p className={styles.comment}>{r.comment}</p>}
            {r.links.length > 0 && (
              <div className={styles.links}>
                {r.links.map((l, i) => (
                  <a key={i} href={l} target="_blank" rel="noopener noreferrer" className={styles.link}>
                    링크 {i + 1}
                  </a>
                ))}
              </div>
            )}
          </li>
        ))}
      </ul>

      {data?.next_cursor && (
        <button className={styles.moreBtn} onClick={handleLoadMore} disabled={loadingMore}>
          {loadingMore ? "불러오는 중..." : "더 보기"}
        </button>
      )}

      {reviews.length === 0 && !showForm && (
        <p className={styles.empty}>아직 리뷰가 없어요. 첫 리뷰를 남겨보세요!</p>
      )}
    </section>
  )
}
