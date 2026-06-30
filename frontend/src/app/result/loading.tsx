import styles from "./loading.module.css"

export default function Loading() {
  return (
    <div className={styles.container}>
      <div className={styles.spinner}>
        <div className={styles.spinnerRing} />
      </div>
      <h2 className={styles.title}>AI가 코스를 짜는 중이에요</h2>
      <p className={styles.sub}>딱 맞는 장소들을 찾고 있어요...</p>
      <div className={styles.cards}>
        {[1, 2, 3].map((i) => (
          <div key={i} className={styles.card} />
        ))}
      </div>
    </div>
  )
}
