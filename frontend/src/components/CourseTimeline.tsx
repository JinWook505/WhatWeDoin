import { PlaceDetail } from "@/lib/api"
import PlaceCard from "./PlaceCard"
import styles from "./CourseTimeline.module.css"

interface Props {
  places: PlaceDetail[]
  courseId: number
  excludedIds?: Set<number>
  onToggleExclude?: (placeId: number) => void
}

export default function CourseTimeline({ places, courseId, excludedIds, onToggleExclude }: Props) {
  return (
    <section className={styles.timeline}>
      {places.map((place, idx) => (
        <div key={place.place_id} className={styles.item}>
          <PlaceCard
            place={place}
            courseId={courseId}
            isExcluded={excludedIds?.has(place.place_id) ?? false}
            onToggleExclude={onToggleExclude ? () => onToggleExclude(place.place_id) : undefined}
          />
          {idx < places.length - 1 && (
            <div className={styles.connector}>
              <span className={styles.connectorLine} />
            </div>
          )}
        </div>
      ))}
    </section>
  )
}
