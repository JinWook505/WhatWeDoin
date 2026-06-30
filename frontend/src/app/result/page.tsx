import { recommend } from "@/lib/api"
import CourseTimeline from "@/components/CourseTimeline"
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
  let errorStatus = 0

  try {
    const res = await recommend(q)
    data = res.data
  } catch (err: unknown) {
    if (err instanceof Error) {
      errorMessage = err.message
      errorStatus = (err as { status?: number }).status ?? 500
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
      <header className={styles.header}>
        <a href="/" className={styles.backLink}>← 다시 검색</a>
        {data.station_name && (
          <span className={styles.station}>{data.station_name} 근처</span>
        )}
        <h1 className={styles.title}>{data.title}</h1>
        {data.description && <p className={styles.desc}>{data.description}</p>}
        {data.total_walking_distance_km != null && (
          <p className={styles.distance}>
            도보 총 {data.total_walking_distance_km.toFixed(1)} km
          </p>
        )}
      </header>

      <CourseTimeline places={data.places} courseId={data.course_id} />

      {data.similar_top_courses.length > 0 && (
        <section className={styles.similar}>
          <h2 className={styles.similarTitle}>비슷한 인기 코스</h2>
          <ul className={styles.similarList}>
            {data.similar_top_courses.slice(0, 3).map((c) => (
              <li key={c.course_id} className={styles.similarItem}>
                {c.title ?? `코스 #${c.course_id}`}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
