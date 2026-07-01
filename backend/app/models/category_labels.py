"""Kakao Local API category_group_code -> Korean label.

places.category stores this raw code (see scripts/etl_places.py's CATEGORIES /
KAKAO_CATEGORY_THEME_MAP for the same fixed official Kakao code list). API
responses translate it for display (D-24) instead of leaking the raw code.
"""

PLACE_CATEGORY_KO: dict[str, str] = {
    "MT1": "대형마트", "CS2": "편의점", "PS3": "어린이집,유치원", "SC4": "학교",
    "AC5": "학원", "PK6": "주차장", "OL7": "주유소,충전소", "SW8": "지하철역",
    "BK9": "은행", "CT1": "문화시설", "AG2": "중개업소", "PO3": "공공기관",
    "AT4": "관광명소", "AD5": "숙박", "FD6": "음식점", "CE7": "카페",
    "HP8": "병원", "PM9": "약국",
}


def place_category_label(category_group_code: str | None) -> str | None:
    if not category_group_code:
        return None
    return PLACE_CATEGORY_KO.get(category_group_code, category_group_code)
