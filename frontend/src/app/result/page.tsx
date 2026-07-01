import { recommend, getCourses, ApiError } from "@/lib/api"
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

  try {
    const res = await recommend(q)
    if (!res.data) throw new ApiError("데이터 없음", 500)

    return (
      <div className={styles.page}>
        <ResultClient initialData={res.data} query={q} />
      </div>
    )
  } catch (err: unknown) {
    const apiErr = err instanceof ApiError ? err : null
    const status = apiErr?.status ?? 500
    const code = apiErr?.code ?? ""

    if (status === 429) {
      return (
        <div className={styles.centered}>
          <p className={styles.limitTitle}>오늘 추천 한도를 모두 사용했어요</p>
          <p className={styles.limitSub}>KST 자정에 초기화됩니다. 내일 다시 이용해주세요.</p>
          <a href="/" className={styles.back}>← 홈으로</a>
        </div>
      )
    }

    if (code === "LLM_UNAVAILABLE") {
      let popularCourses: Awaited<ReturnType<typeof getCourses>>["courses"] = []
      try {
        const resp = await getCourses({ sort: "score", limit: 3 })
        popularCourses = resp.courses
      } catch {
        // best-effort: show fallback without popular courses if fetch fails
      }
      return <ErrorFallback type="LLM_UNAVAILABLE" query={q} popularCourses={popularCourses} />
    }

    if (code === "UPSTREAM_UNAVAILABLE") {
      return <ErrorFallback type="UPSTREAM_UNAVAILABLE" query={q} />
    }

    return (
      <ErrorFallback
        type="GENERIC"
        query={q}
        message={apiErr?.message}
      />
    )
  }
}
