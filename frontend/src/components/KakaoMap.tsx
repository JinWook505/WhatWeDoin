"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import { StationResult } from "@/lib/api"
import styles from "./KakaoMap.module.css"

const API_URL =
  typeof window === "undefined"
    ? (process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://backend:8080")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080")

interface Props {
  selectedStation?: StationResult | null
  onStationSelect?: (station: StationResult) => void
  height?: string
}

declare global {
  interface Window {
    kakao: any
  }
}

async function fetchStationsInBounds(bounds: {
  sw: { lat: number; lng: number }
  ne: { lat: number; lng: number }
}): Promise<StationResult[]> {
  const params = new URLSearchParams({
    bounds: `${bounds.sw.lat},${bounds.sw.lng},${bounds.ne.lat},${bounds.ne.lng}`,
  })
  const res = await fetch(`${API_URL}/v1/stations?${params}`, { cache: "no-store" })
  if (!res.ok) return []
  const data = await res.json()
  return Array.isArray(data) ? data : (data.data ?? [])
}

export default function KakaoMap({ selectedStation, onStationSelect, height = "300px" }: Props) {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)
  const markersRef = useRef<any[]>([])
  const selectedMarkerRef = useRef<any>(null)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState(false)

  const clearMarkers = () => {
    markersRef.current.forEach((m) => m.setMap(null))
    markersRef.current = []
  }

  const loadMarkersForBounds = useCallback(async () => {
    const map = mapInstanceRef.current
    if (!map || !window.kakao) return

    const bounds = map.getBounds()
    const sw = bounds.getSouthWest()
    const ne = bounds.getNorthEast()

    const stations = await fetchStationsInBounds({
      sw: { lat: sw.getLat(), lng: sw.getLng() },
      ne: { lat: ne.getLat(), lng: ne.getLng() },
    })

    clearMarkers()

    stations.forEach((station) => {
      const pos = new window.kakao.maps.LatLng(station.lat, station.lng)
      const isSelected = selectedStation?.station_id === station.station_id

      const markerImage = isSelected
        ? new window.kakao.maps.MarkerImage(
            "https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png",
            new window.kakao.maps.Size(31, 35),
          )
        : undefined

      const marker = new window.kakao.maps.Marker({
        position: pos,
        title: station.name,
        ...(markerImage ? { image: markerImage } : {}),
      })
      marker.setMap(map)

      if (onStationSelect) {
        window.kakao.maps.event.addListener(marker, "click", () => {
          onStationSelect(station)
        })
      }

      markersRef.current.push(marker)
    })
  }, [selectedStation, onStationSelect])

  // Initialise SDK + map
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
          level: 8,
        })
        mapInstanceRef.current = map
        setReady(true)

        window.kakao.maps.event.addListener(map, "dragend", loadMarkersForBounds)
        window.kakao.maps.event.addListener(map, "zoom_changed", loadMarkersForBounds)
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

  // Load markers once map is ready, and whenever selectedStation changes
  useEffect(() => {
    if (ready) {
      loadMarkersForBounds()
    }
  }, [ready, loadMarkersForBounds])

  // Pan to selected station
  useEffect(() => {
    if (!ready || !selectedStation || !mapInstanceRef.current || !window.kakao) return
    const pos = new window.kakao.maps.LatLng(selectedStation.lat, selectedStation.lng)
    mapInstanceRef.current.panTo(pos)
  }, [ready, selectedStation])

  if (error) {
    return (
      <div className={styles.fallback} style={{ height }}>
        <span>지도를 불러올 수 없어요</span>
        <span className={styles.fallbackSub}>NEXT_PUBLIC_KAKAO_MAP_KEY를 설정해주세요</span>
      </div>
    )
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
