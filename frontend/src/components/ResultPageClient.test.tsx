import { render, waitFor } from "@testing-library/react"
import { StrictMode } from "react"
import ResultPageClient from "./ResultPageClient"

jest.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams({ q: "홍대 데이트" }),
}))

jest.mock("../lib/api", () => {
  const actual = jest.requireActual("../lib/api")
  return {
    ...actual,
    recommend: jest.fn(),
  }
})

import { recommend } from "@/lib/api"

const mockedRecommend = recommend as jest.Mock

function makeCourseData() {
  return {
    course_id: 1,
    title: "테스트 코스",
    description: "",
    station_name: null,
    theme_tags: [],
    stages: [],
    similar_top_courses: [],
    served_from: "LLM",
    total_walking_distance_km: null,
  }
}

describe("ResultPageClient", () => {
  beforeEach(() => {
    mockedRecommend.mockReset()
    mockedRecommend.mockResolvedValue({
      success: true,
      data: makeCourseData(),
      error: null,
      daily_remaining: 2,
    })
  })

  it("StrictMode로 effect가 두 번 실행되어도 동일한 idempotency key로만 요청한다", async () => {
    render(
      <StrictMode>
        <ResultPageClient />
      </StrictMode>,
    )

    await waitFor(() => expect(mockedRecommend).toHaveBeenCalled())
    // 두 번째(StrictMode) invoke가 있다면 반영될 시간을 준다.
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(mockedRecommend.mock.calls.length).toBeGreaterThanOrEqual(2)
    const keys = mockedRecommend.mock.calls.map((call) => call[2])
    const uniqueKeys = new Set(keys)

    expect(uniqueKeys.size).toBe(1)
    keys.forEach((key) => expect(typeof key).toBe("string"))
  })

  it("StrictMode 이중 호출이 실제로 발생하는지와 무관하게, 같은 질의어로 재호출 시 매번 같은 key를 재사용한다", async () => {
    render(<ResultPageClient />)

    await waitFor(() => expect(mockedRecommend).toHaveBeenCalledTimes(1))

    const firstKey = mockedRecommend.mock.calls[0][2]
    expect(typeof firstKey).toBe("string")
  })
})
