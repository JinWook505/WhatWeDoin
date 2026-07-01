"use client"

import { useEffect, useRef, useState } from "react"
import { PlaceDetail, StageDetail } from "@/lib/api"
import styles from "./CourseMap.module.css"

interface Props {
  stages: StageDetail[]
  excludedIds?: Set<number>
  height?: string
}

declare global {
  interface Window {
    kakao: any
  }
}

interface MarkedPlace {
  place: PlaceDetail
  stageOrder: number
}

function collectMarkedPlaces(stages: StageDetail[]): MarkedPlace[] {
  const result: MarkedPlace[] = []
  for (const stage of stages) {
    for (const place of stage.options) {
      if (place.lat != null && place.lng != null) {
        result.push({ place, stageOrder: stage.stage_order })
      }
    }
  }
  return result
}

export default function CourseMap({ stages, excludedIds, height = "260px" }: Props) {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)
  const markersRef = useRef<any[]>([])
  const [ready, setReady] = useState(false)
  const [error, setError] = useState(false)

  const markedPlaces = collectMarkedPlaces(stages)

  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_KAKAO_MAP_KEY
    if (!key) {
      setError(true)
      return
    }

    const initMap = () => {
      if (!mapRef.current) return
      window.kakao.maps.load(() => {
        const center = new window.kakao.maps.LatLng(37.5665, 126.978)
        const map = new window.kakao.maps.Map(mapRef.current, {
          center,
          level: 6,
        })
        mapInstanceRef.current = map
        setReady(true)
      })
    }

    if (window.kakao?.maps) {
      initMap()
      return
    }

    const existing = document.querySelector('script[data-kakaomap]')
    if (existing) {
      existing.addEventListener("load", initMap)
      return
    }

    const script = document.createElement("script")
    script.setAttribute("data-kakaomap", "true")
    script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${key}&autoload=false`
    script.async = true
    script.onload = initMap
    script.onerror = () => setError(true)
    document.head.appendChild(script)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!ready || !map || !window.kakao) return

    markersRef.current.forEach((m) => m.setMap(null))
    markersRef.current = []

    if (markedPlaces.length === 0) return

    const bounds = new window.kakao.maps.LatLngBounds()

    markedPlaces.forEach(({ place, stageOrder }) => {
      const isExcluded = excludedIds?.has(place.place_id) ?? false
      const pos = new window.kakao.maps.LatLng(place.lat, place.lng)

      const marker = new window.kakao.maps.Marker({
        position: pos,
        title: place.name,
        opacity: isExcluded ? 0.35 : 1,
      })
      marker.setMap(map)

      const infoWindow = new window.kakao.maps.InfoWindow({
        content: `<div style="padding:4px 8px;font-size:12px;white-space:nowrap;">${stageOrder}단계 · ${place.name}</div>`,
      })
      window.kakao.maps.event.addListener(marker, "mouseover", () => infoWindow.open(map, marker))
      window.kakao.maps.event.addListener(marker, "mouseout", () => infoWindow.close())

      markersRef.current.push(marker)
      bounds.extend(pos)
    })

    map.setBounds(bounds)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, stages, excludedIds])

  if (error) {
    return (
      <div className={styles.fallback} style={{ height }}>
        <span>지도를 불러올 수 없어요</span>
        <span className={styles.fallbackSub}>NEXT_PUBLIC_KAKAO_MAP_KEY를 설정해주세요</span>
      </div>
    )
  }

  if (markedPlaces.length === 0) {
    return null
  }

  return (
    <div className={styles.wrapper} style={{ height }}>
      <div ref={mapRef} className={styles.map} />
      {!ready && (
        <div className={styles.loading}>
          <span>지도를 불러오는 중...</span>
        </div>
      )}
    </div>
  )
}
