// Single source of truth for backend enum <-> Korean label mappings.
// Keep in sync with backend/app/models/enums.py.
export interface EnumOption {
  value: string
  label: string
}

export const THEME_TAG_OPTIONS: EnumOption[] = [
  { value: "FOOD", label: "맛집" },
  { value: "CAFE", label: "카페" },
  { value: "BAR", label: "술집" },
  { value: "BOARD_GAME", label: "보드게임" },
  { value: "KARAOKE", label: "노래방" },
  { value: "ARCADE", label: "오락" },
  { value: "PARK", label: "공원" },
  { value: "CULTURE", label: "전시/문화" },
  { value: "SHOPPING", label: "쇼핑" },
  { value: "NIGHT_VIEW", label: "야경" },
  { value: "MOVIE", label: "영화" },
  { value: "ACTIVITY", label: "액티비티" },
]

export const COMPANION_TYPE_OPTIONS: EnumOption[] = [
  { value: "SOLO", label: "혼자" },
  { value: "FRIEND", label: "친구" },
  { value: "COUPLE", label: "연인" },
  { value: "FAMILY", label: "가족" },
]

export const BUDGET_TIER_OPTIONS: EnumOption[] = [
  { value: "UNDER_30000", label: "~3만원" },
  { value: "30000_70000", label: "3~7만원" },
  { value: "70000_150000", label: "7~15만원" },
  { value: "OVER_150000", label: "15만원~" },
]

export const GENDER_OPTIONS: EnumOption[] = [
  { value: "FEMALE", label: "여성" },
  { value: "MALE", label: "남성" },
  { value: "OTHER", label: "기타" },
]

export const DATING_STAGE_OPTIONS: EnumOption[] = [
  { value: "SOME", label: "썸" },
  { value: "EARLY", label: "초기" },
  { value: "LONGTERM", label: "장기" },
]

function toLabelMap(options: EnumOption[]): Record<string, string> {
  return Object.fromEntries(options.map((o) => [o.value, o.label]))
}

export const THEME_TAG_KO = toLabelMap(THEME_TAG_OPTIONS)
export const COMPANION_TYPE_KO = toLabelMap(COMPANION_TYPE_OPTIONS)
export const BUDGET_TIER_KO = toLabelMap(BUDGET_TIER_OPTIONS)
export const GENDER_KO = toLabelMap(GENDER_OPTIONS)
export const DATING_STAGE_KO = toLabelMap(DATING_STAGE_OPTIONS)
