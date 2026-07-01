"use client"

import { useState } from "react"
import { PlaceDetail } from "@/lib/api"
import ReportBottomSheet from "./ReportBottomSheet"
import styles from "./PlaceCard.module.css"

interface Props {
  place: PlaceDetail
  courseId: number
  isExcluded?: boolean
  onToggleExclude?: () => void
}

function hasHours(bh: PlaceDetail["business_hours"]): boolean {
  if (bh == null) return false
  if (typeof bh === "object" && !Array.isArray(bh)) return Object.keys(bh).length > 0
  return Boolean(bh)
}

export default function PlaceCard({ place, courseId, isExcluded = false, onToggleExclude }: Props) {
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
      <article className={`${styles.card} ${isExcluded ? styles.excluded : ""}`}>
        {place.walking_distance_from_station_km != null && (
          <div className={styles.distanceBadge} aria-label="역에서 도보 거리">
            🚶 {place.walking_distance_from_station_km.toFixed(1)}km
          </div>
        )}

        <div className={styles.body}>
          <div className={styles.topRow}>
            <div className={styles.nameBlock}>
              <div className={styles.nameRow}>
                <h3 className={styles.name}>{place.name}</h3>
                {place.status === "CLOSED" && (
                  <span className={styles.closedBadge}>폐업</span>
                )}
              </div>
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
              {typeof place.business_hours === "string"
                ? place.business_hours
                : JSON.stringify(place.business_hours)}
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
            {onToggleExclude && (
              <button
                className={isExcluded ? styles.includeBtn : styles.excludeBtn}
                onClick={onToggleExclude}
              >
                {isExcluded ? "다시 포함" : "이 장소 빼기"}
              </button>
            )}
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
