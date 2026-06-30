"use client"

import { useState } from "react"
import { PlaceDetail } from "@/lib/api"
import ReportBottomSheet from "./ReportBottomSheet"
import styles from "./PlaceCard.module.css"

interface Props {
  place: PlaceDetail
  courseId: number
}

function hasHours(bh: PlaceDetail["business_hours"]): boolean {
  if (bh == null) return false
  if (typeof bh === "object" && !Array.isArray(bh)) return Object.keys(bh).length > 0
  return Boolean(bh)
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
        <div className={styles.orderBadge} aria-label={`${place.order}번째 장소`}>
          {place.order}
        </div>

        <div className={styles.body}>
          <div className={styles.topRow}>
            <div className={styles.nameBlock}>
              <h3 className={styles.name}>{place.name}</h3>
              {place.price_range && (
                <span className={styles.price}>{place.price_range}</span>
              )}
            </div>

            {displayCount > 0 && (
              <div className={styles.ratingBlock}>
                <span className={styles.rating}>
                  ★ {displayRating?.toFixed(1)}
                  <span className={styles.ratingCount}>{displayCount}명</span>
                </span>
              </div>
            )}
          </div>

          {place.description && (
            <p className={styles.description}>{place.description}</p>
          )}

          {hasHours(place.business_hours) ? (
            <p className={styles.hours}>
              {JSON.stringify(place.business_hours)}
            </p>
          ) : (
            <span className={styles.noHours}>영업시간 미등록</span>
          )}

          <div className={styles.actions}>
            {place.map_url && (
              <a
                className={styles.mapLink}
                href={place.map_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                카카오맵 보기
              </a>
            )}
            <button
              className={styles.reportBtn}
              onClick={() => setSheetOpen(true)}
            >
              정보 제보
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
