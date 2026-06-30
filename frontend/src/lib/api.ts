// Server-side uses internal Docker network URL; client-side uses public URL (browser-accessible)
const API_URL =
  typeof window === "undefined"
    ? (process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://backend:8080")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080")

export interface StationResult {
  station_id: number
  name: string
  lat: number
  lng: number
}

export interface PlaceDetail {
  order: number
  place_id: number
  name: string
  category: string | null
  address: string | null
  business_hours: Record<string, unknown> | null
  price_range: string | null
  user_rating_avg: number | null
  user_rating_count: number
  map_url: string | null
  thumbnail_url: string | null
  description: string
}

export interface CourseData {
  course_id: number
  title: string
  description: string
  station_name: string | null
  theme_tags: string[]
  places: PlaceDetail[]
  total_walking_distance_km: number | null
  similar_top_courses: { course_id: number; title: string; bayesian_score: number }[]
  served_from: string
}

export interface RecommendResponse {
  success: boolean
  data: CourseData | null
  error: string | null
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

export async function searchStations(q: string): Promise<StationResult[]> {
  const res = await fetch(
    `${API_URL}/v1/stations?q=${encodeURIComponent(q)}&limit=10`,
    { cache: "no-store" },
  )
  if (!res.ok) throw new ApiError("역 검색 실패", res.status)
  return res.json()
}

export async function recommend(
  query: string,
  excludePlaceIds: number[] = [],
): Promise<RecommendResponse> {
  const res = await fetch(`${API_URL}/v1/courses/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      exclude_place_ids: excludePlaceIds,
    }),
    cache: "no-store",
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(
      body?.detail?.message ?? body?.detail ?? `HTTP ${res.status}`,
      res.status,
      body?.detail?.code,
    )
  }
  return res.json()
}

export async function reportPlace(
  placeId: number,
  payload: { rating?: number; business_hours_text?: string; price_range?: string },
): Promise<void> {
  const res = await fetch(`${API_URL}/v1/places/${placeId}/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(body?.detail ?? `HTTP ${res.status}`, res.status)
  }
}
