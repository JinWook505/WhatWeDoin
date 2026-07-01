import { StageDetail } from "@/lib/api"
import PlaceCard from "./PlaceCard"
import styles from "./CourseTimeline.module.css"

interface Props {
  stages: StageDetail[]
  courseId: number
  excludedIds?: Set<number>
  onToggleExclude?: (placeId: number) => void
}

export default function CourseTimeline({ stages, courseId, excludedIds, onToggleExclude }: Props) {
  return (
    <section className={styles.timeline}>
      {stages.map((stage, idx) => (
        <div key={stage.stage_order} className={styles.item}>
          <h3 className={styles.stageHeader}>
            {stage.stage_order}단계 · {stage.stage_label}
            {stage.options.length > 1 && <span className={styles.pickOne}>택1</span>}
          </h3>
          <div className={styles.optionsRow}>
            {stage.options.map((place) => (
              <PlaceCard
                key={place.place_id}
                place={place}
                courseId={courseId}
                isExcluded={excludedIds?.has(place.place_id) ?? false}
                onToggleExclude={onToggleExclude ? () => onToggleExclude(place.place_id) : undefined}
              />
            ))}
          </div>
          {idx < stages.length - 1 && (
            <div className={styles.connector}>
              <span className={styles.connectorLine} />
            </div>
          )}
        </div>
      ))}
    </section>
  )
}
