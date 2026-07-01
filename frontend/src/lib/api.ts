import { getAccessToken } from "@/lib/auth"

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
  daily_remaining?: number | null
}

export interface ClarificationResponse {
  status: "NEEDS_CLARIFICATION"
  partial_parsed_input: {
    theme_tags?: string[]
    budget_tier?: string | null
    companion_type?: string | null
    head_count?: number
    station_name?: string
  }
  missing_fields: string[]
}

export type RecommendResult = RecommendResponse | ClarificationResponse

export function isClarificationResult(
  res: RecommendResult,
): res is ClarificationResponse {
  return (res as ClarificationResponse).status === "NEEDS_CLARIFICATION"
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

export interface PlaceholderResult {
  placeholder: string
  source: "RECENT" | "WEATHER" | "TIME" | "DEFAULT"
  weather: { temp: number; description: string; main: string } | null
}

export async function getPlaceholder(): Promise<PlaceholderResult> {
  const token = typeof window !== "undefined" ? getAccessToken() : null
  const res = await fetch(`${API_URL}/v1/recommend/placeholder`, {
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new ApiError("placeholder 조회 실패", res.status)
  const body = await res.json()
  return body.data as PlaceholderResult
}

export async function recommend(
  query: string,
  excludePlaceIds: number[] = [],
  idempotencyKey?: string,
  resolved?: { stationId?: number; parsedInput?: Record<string, unknown> },
): Promise<RecommendResult> {
  const token = typeof window !== "undefined" ? getAccessToken() : null
  const ikey = idempotencyKey ?? crypto.randomUUID()
  const res = await fetch(`${API_URL}/v1/courses/recommend`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": ikey,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      query,
      exclude_place_ids: excludePlaceIds,
      ...(resolved?.stationId != null ? { station_id: resolved.stationId } : {}),
      ...(resolved?.parsedInput ? { parsed_input: resolved.parsedInput } : {}),
    }),
    cache: "no-store",
  } as RequestInit)
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

export interface CourseListItem {
  course_id: number
  station_name: string | null
  theme_tags: string[]
  budget_tier: string | null
  companion_type: string | null
  head_count: number | null
  bayesian_score: number
  rating_count: number
  preview_places: string[]
  total_walking_distance_km: number | null
  created_at: string | null
}

export interface CourseListResponse {
  courses: CourseListItem[]
  next_cursor: string | null
}

export interface ReviewItem {
  review_id: number
  score: number
  comment: string | null
  links: string[]
  is_mine: boolean
  created_at: string | null
}

export interface ReviewsResponse {
  summary: {
    bayesian_score: number
    avg_score: number | null
    rating_count: number
  }
  reviews: ReviewItem[]
  next_cursor: string | null
}

export async function getReviews(courseId: number, cursor?: string): Promise<ReviewsResponse> {
  const url = new URL(`${API_URL}/v1/courses/${courseId}/reviews`)
  if (cursor) url.searchParams.set("cursor", cursor)
  const res = await fetch(url.toString(), { cache: "no-store" })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(body?.detail?.message ?? `HTTP ${res.status}`, res.status)
  }
  const json = await res.json()
  return json.data as ReviewsResponse
}

export async function upsertReview(
  courseId: number,
  body: { score: number; comment?: string; links?: string[] },
): Promise<void> {
  const token = typeof window !== "undefined" ? getAccessToken() : null
  const res = await fetch(`${API_URL}/v1/courses/${courseId}/reviews`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new ApiError(b?.detail?.message ?? `HTTP ${res.status}`, res.status)
  }
}

export async function deleteMyReview(courseId: number): Promise<void> {
  const token = typeof window !== "undefined" ? getAccessToken() : null
  const res = await fetch(`${API_URL}/v1/courses/${courseId}/reviews/me`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new ApiError(b?.detail?.message ?? `HTTP ${res.status}`, res.status)
  }
}

export async function getCourses(params: {
  theme?: string[]
  companion_type?: string
  budget_tier?: string
  sort?: "score" | "recent"
  limit?: number
  cursor?: string
}): Promise<CourseListResponse> {
  const url = new URL(`${API_URL}/v1/courses`)
  if (params.theme?.length) {
    for (const t of params.theme) url.searchParams.append("theme", t)
  }
  if (params.companion_type) url.searchParams.set("companion_type", params.companion_type)
  if (params.budget_tier) url.searchParams.set("budget_tier", params.budget_tier)
  if (params.sort) url.searchParams.set("sort", params.sort)
  if (params.limit) url.searchParams.set("limit", String(params.limit))
  if (params.cursor) url.searchParams.set("cursor", params.cursor)

  const res = await fetch(url.toString(), { cache: "no-store" })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(body?.detail?.message ?? `HTTP ${res.status}`, res.status)
  }
  const json = await res.json()
  return json.data as CourseListResponse
}
