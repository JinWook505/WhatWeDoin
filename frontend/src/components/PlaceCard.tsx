"use client"

import { useState } from "react"
import { PlaceDetail } from "@/lib/api"
import ReportBottomSheet from "./ReportBottomSheet"
import styles from "./PlaceCard.module.css"

interface Props {
  place: PlaceDetail
  courseId: number
}

export default function PlaceCard({ place, courseId }: Props) {
  const [sheetOpen, setSheetOpen] = useState(false)
  const [optimisticRating, setOptimisticRating] = useState<number | null>(null)
  const [optimisticCount, setOptimisticCount] = useState<number | null>(null)

  const displayRating = optimisticRating ?? place.user_rating_avg
  const displayCount = optimisticCount ?? place.user_rating_count

  const handleReportSuccess = (rating?: number) => {
    if (rating != null) {
      const prevSum = (place.user_rating_avg ?? 0) * place.user_rating_count
      const newCount = (optimisticCount ?? place.user_rating_count) + 1
      const newAvg = (prevSum + rating) / newCount
      setOptimisticRating(Math.round(newAvg * 10) / 10)
      setOptimisticCount(newCount)
    }
    setSheetOpen(false)
  }

  return (
    <>
      <article className={styles.card}>
        <div className={styles.orderBadge}>{place.order}</div>

        <div className={styles.body}>
          <div className={styles.topRow}>
            <div>
              <h3 className={styles.name}>{place.name}</h3>
              <div className={styles.meta}>
                {place.category && <span className={styles.category}>{place.category}</span>}
                {place.price_range && (
                  <span className={styles.price}>{place.price_range}</span>
                )}
              </div>
            </div>

            {/* rating */}
            <div className={styles.ratingBlock}>
              {displayCount > 0 ? (
                <span className={styles.rating}>
                  ★ {displayRating?.toFixed(1)} · {displayCount}명
                </span>
              ) : (
                <button
                  className={styles.ctaSmall}
                  onClick={() => setSheetOpen(true)}
                >
                  별점 남기기
                </button>
              )}
            </div>
          </div>

          {place.description && (
            <p className={styles.description}>{place.description}</p>
          )}

          {/* business hours */}
          {place.business_hours != null ? (
            <p className={styles.hours}>
              {JSON.stringify(place.business_hours)}
            </p>
          ) : (
            <button
              className={styles.ctaHours}
              onClick={() => setSheetOpen(true)}
            >
              영업시간 미확인 — 알고 계신가요? 제보하기
            </button>
          )}

          {/* actions */}
          <div className={styles.actions}>
            {place.map_url && (
              <a
                className={styles.mapLink}
                href={place.map_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                카카오맵에서 보기 →
              </a>
            )}
            <button
              className={styles.reportBtn}
              onClick={() => setSheetOpen(true)}
            >
              제보하기
            </button>
          </div>
        </div>
      </article>

      {sheetOpen && (
        <ReportBottomSheet
          placeId={place.place_id}
          placeName={place.name}
          onClose={() => setSheetOpen(false)}
          onSuccess={handleReportSuccess}
        />
      )}
    </>
  )
}
