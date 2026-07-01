"use client"

import Link from "next/link"
import styles from "./SimilarCourses.module.css"

interface SimilarCourse {
  course_id: number
  title: string
  bayesian_score: number
}

interface Props {
  courses: SimilarCourse[]
}

export default function SimilarCourses({ courses }: Props) {
  if (!courses.length) return null

  return (
    <section className={styles.section}>
      <h2 className={styles.title}>비슷한 인기 코스</h2>
      <div className={styles.scroll}>
        {courses.slice(0, 3).map((c) => (
          <Link
            key={c.course_id}
            href={`/courses/${c.course_id}`}
            className={styles.card}
          >
            <div className={styles.scoreBadge}>
              ★ {c.bayesian_score.toFixed(1)}
            </div>
            <p className={styles.cardTitle}>{c.title ?? `코스 #${c.course_id}`}</p>
            <span className={styles.arrow}>→</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
