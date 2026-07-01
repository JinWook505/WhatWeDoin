import { render, screen } from "@testing-library/react"
import QuotaBadge from "./QuotaBadge"
import { setTokens, logout, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from "@/lib/auth"
import { incrementUsedCount } from "@/lib/quota"

describe("QuotaBadge", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it("로그아웃하면 새로고침 없이 로그인 유도 문구로 즉시 전환된다", async () => {
    setTokens("access-token", "refresh-token")
    incrementUsedCount()
    render(<QuotaBadge />)

    expect(await screen.findByText("2")).not.toBeNull()

    global.fetch = jest.fn().mockResolvedValue({ ok: true } as Response)
    await logout()

    expect(await screen.findByText("로그인 후 AI 추천 하루 3회 무료")).not.toBeNull()
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull()
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull()
  })
})
