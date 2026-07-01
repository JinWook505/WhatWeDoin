"use client"

import { useState } from "react"
import ReportBottomSheet from "./ReportBottomSheet"
import styles from "./PlaceReportButton.module.css"

interface Props {
  placeId: number
  placeName: string
}

export default function PlaceReportButton({ placeId, placeName }: Props) {
  const [open, setOpen] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  return (
    <>
      <button type="button" className={styles.reportBtn} onClick={() => setOpen(true)}>
        {submitted ? "제보 완료 ✓" : "정보 제보"}
      </button>
      {open && (
        <ReportBottomSheet
          placeId={placeId}
          placeName={placeName}
          onClose={() => setOpen(false)}
          onSuccess={() => { setOpen(false); setSubmitted(true) }}
        />
      )}
    </>
  )
}
