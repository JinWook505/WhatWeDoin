import { recommend, ApiError } from "@/lib/api"
import ResultClient from "@/components/ResultClient"
import ErrorFallback from "@/components/ErrorFallback"
import styles from "./page.module.css"

interface Props {
  searchParams: Promise<{
    q?: string
  }>
}

export default async function ResultPage({ searchParams }: Props) {
  const { q } = await searchParams

  if (!q) {
    return (
      <div className={styles.centered}>
        <p>검색 정보가 없습니다.</p>
        <a href="/" className={styles.back}>← 홈으로 돌아가기</a>
      </div>
    )
  }

  let data = null
  let errorMessage: string | null = null
  let errorCode: string | undefined
  let errorStatus = 0
  let dailyRemaining: number | null = null

  try {
    const res = await recommend(q)
    data = res.data
    dailyRemaining = res.daily_remaining ?? null
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      errorMessage = err.message
      errorStatus = err.status
      errorCode = err.code
    } else if (err instanceof Error) {
      errorMessage = err.message
      errorStatus = 500
    }
  }

  if (errorStatus > 0 || !data) {
    return (
      <ErrorFallback
        status={errorStatus || undefined}
        code={errorCode}
        message={errorMessage ?? undefined}
      />
    )
  }

  return (
    <div className={styles.page}>
      <ResultClient initialData={data} query={q} dailyRemaining={dailyRemaining} />
    </div>
  )
}
