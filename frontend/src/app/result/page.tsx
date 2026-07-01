import { recommend, ApiError } from "@/lib/api"
import ResultClient from "@/components/ResultClient"
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

  if (errorStatus === 429) {
    return (
      <div className={styles.centered}>
        <p className={styles.limitTitle}>오늘 추천 한도를 모두 사용했어요</p>
        <p className={styles.limitSub}>KST 자정에 초기화됩니다. 내일 다시 이용해주세요.</p>
        <a href="/" className={styles.back}>← 홈으로</a>
      </div>
    )
  }

  if (errorCode === "INVALID_QUERY") {
    return (
      <div className={styles.centered}>
        <p className={styles.limitTitle}>질문을 조금 더 구체적으로 써줘요</p>
        <p className={styles.limitSub}>{errorMessage ?? "지하철역 이름과 어떻게 놀고 싶은지를 포함해주세요."}</p>
        <a href="/" className={styles.back}>← 다시 쓰기</a>
      </div>
    )
  }

  if (errorMessage || !data) {
    return (
      <div className={styles.centered}>
        <p>코스 생성 중 오류가 발생했습니다.</p>
        <p className={styles.errorDetail}>{errorMessage}</p>
        <a href="/" className={styles.back}>← 다시 시도</a>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <ResultClient initialData={data} query={q} dailyRemaining={dailyRemaining} />
    </div>
  )
}
