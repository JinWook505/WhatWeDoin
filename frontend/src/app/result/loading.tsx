import styles from "./page.module.css"

export default function Loading() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <a href="/" className={styles.backLink}>← 다시 검색</a>
        <div className={styles.loadingTitle} />
        <div className={styles.loadingDesc} />
      </header>
      <div className={styles.loadingCards}>
        {[1, 2, 3].map((i) => (
          <div key={i} className={styles.loadingCard} />
        ))}
      </div>
      <p className={styles.loadingHint}>AI가 코스를 생성하는 중이에요…</p>
    </div>
  )
}
