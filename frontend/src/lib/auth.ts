import { resetUsedCount } from "@/lib/quota"

const API_URL =
  typeof window === "undefined"
    ? (process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://backend:8080")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080")

export const ACCESS_TOKEN_KEY = "wwd_access"
export const REFRESH_TOKEN_KEY = "wwd_refresh"

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens(access: string, refresh: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(ACCESS_TOKEN_KEY, access)
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
}

export function clearTokens(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function isLoggedIn(): boolean {
  return Boolean(getAccessToken())
}

export async function refreshIfNeeded(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null

  try {
    const res = await fetch(`${API_URL}/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!res.ok) {
      clearTokens()
      return null
    }
    const data = await res.json()
    const { access_token, refresh_token } = data.data ?? {}
    if (access_token && refresh_token) {
      setTokens(access_token, refresh_token)
      return access_token
    }
    clearTokens()
    return null
  } catch {
    return null
  }
}

export async function fetchWithAuth(
  input: RequestInfo,
  init: RequestInit = {},
): Promise<Response> {
  let token = getAccessToken()

  const doFetch = (t: string | null) =>
    fetch(input, {
      ...init,
      headers: {
        ...(init.headers ?? {}),
        ...(t ? { Authorization: `Bearer ${t}` } : {}),
      },
    })

  let res = await doFetch(token)

  if (res.status === 401 && token) {
    token = await refreshIfNeeded()
    if (token) {
      res = await doFetch(token)
    } else {
      clearTokens()
      window.location.href = "/?login_error=1"
    }
  }

  return res
}

export async function logout(): Promise<void> {
  const token = getAccessToken()
  if (token) {
    try {
      await fetch(`${API_URL}/v1/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
    } catch {
      // ignore errors — tokens are cleared locally regardless
    }
  }
  clearTokens()
  resetUsedCount()
}
