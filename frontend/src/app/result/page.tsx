import { Suspense } from "react"
import ResultPageClient from "@/components/ResultPageClient"
import styles from "./page.module.css"

export default function ResultPage() {
  return (
    <div className={styles.page}>
      <Suspense fallback={<div className={styles.centered}>불러오는 중...</div>}>
        <ResultPageClient />
      </Suspense>
    </div>
  )
}
