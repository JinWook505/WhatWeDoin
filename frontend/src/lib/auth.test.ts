import { setTokens, logout, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from "./auth"
import { incrementUsedCount, getRemainingCount } from "./quota"

describe("logout", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it("clears tokens but does not reset today's quota counter", async () => {
    setTokens("access-token", "refresh-token")
    incrementUsedCount()
    incrementUsedCount()
    incrementUsedCount()
    expect(getRemainingCount()).toBe(0)

    global.fetch = jest.fn().mockResolvedValue({ ok: true } as Response)

    await logout()

    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull()
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull()
    expect(getRemainingCount()).toBe(0)
  })

  it("does not reset quota counter even if the logout request fails", async () => {
    setTokens("access-token", "refresh-token")
    incrementUsedCount()
    expect(getRemainingCount()).toBe(2)

    global.fetch = jest.fn().mockRejectedValue(new Error("network error"))

    await logout()

    expect(getRemainingCount()).toBe(2)
  })
})
