import { PlaceDetail } from "@/lib/api"
import PlaceCard from "./PlaceCard"
import styles from "./CourseTimeline.module.css"

interface Props {
  places: PlaceDetail[]
  courseId: number
}

export default function CourseTimeline({ places, courseId }: Props) {
  return (
    <section className={styles.timeline}>
      {places.map((place, idx) => (
        <div key={place.place_id} className={styles.item}>
          <PlaceCard place={place} courseId={courseId} />
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
