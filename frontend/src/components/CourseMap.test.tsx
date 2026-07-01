import { render, screen } from "@testing-library/react"
import CourseMap from "./CourseMap"
import { PlaceDetail, StageDetail } from "@/lib/api"

function makePlace(overrides: Partial<PlaceDetail> = {}): PlaceDetail {
  return {
    place_id: 1,
    name: "테스트 장소",
    category: null,
    address: null,
    business_hours: null,
    price_range: null,
    user_rating_avg: null,
    user_rating_count: 0,
    map_url: null,
    thumbnail_url: null,
    description: "",
    walking_distance_from_station_km: null,
    lat: 37.5,
    lng: 127.0,
    ...overrides,
  }
}

function makeStages(places: PlaceDetail[]): StageDetail[] {
  return [{ stage_order: 1, stage_label: "1단계", options: places }]
}

describe("CourseMap", () => {
  const originalKey = process.env.NEXT_PUBLIC_KAKAO_MAP_KEY

  afterEach(() => {
    process.env.NEXT_PUBLIC_KAKAO_MAP_KEY = originalKey
    document.head.innerHTML = ""
  })

  it("NEXT_PUBLIC_KAKAO_MAP_KEY 미설정 시 폴백 문구를 보여준다", () => {
    delete process.env.NEXT_PUBLIC_KAKAO_MAP_KEY

    render(<CourseMap stages={makeStages([makePlace()])} />)

    expect(screen.getByText("지도를 불러올 수 없어요")).toBeInTheDocument()
  })

  it("모든 place에 좌표가 없으면 에러 없이 아무것도 렌더링하지 않는다", () => {
    process.env.NEXT_PUBLIC_KAKAO_MAP_KEY = "test-key"

    const { container } = render(
      <CourseMap stages={makeStages([makePlace({ lat: null, lng: null })])} />,
    )

    expect(container).toBeEmptyDOMElement()
  })

  it("일부 place에만 좌표가 없어도 에러 없이 렌더링된다", () => {
    process.env.NEXT_PUBLIC_KAKAO_MAP_KEY = "test-key"

    expect(() =>
      render(
        <CourseMap
          stages={makeStages([
            makePlace({ place_id: 1, lat: 37.5, lng: 127.0 }),
            makePlace({ place_id: 2, lat: null, lng: null }),
          ])}
        />,
      ),
    ).not.toThrow()
  })
})
