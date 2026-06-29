import enum


class OAuthProvider(str, enum.Enum):
    KAKAO = "KAKAO"
    NAVER = "NAVER"


class GenderType(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class DatingStage(str, enum.Enum):
    SOME = "SOME"
    EARLY = "EARLY"
    LONGTERM = "LONGTERM"
    UNKNOWN = "UNKNOWN"


class BudgetTier(str, enum.Enum):
    UNDER_30000 = "UNDER_30000"
    BETWEEN_30000_70000 = "30000_70000"
    BETWEEN_70000_150000 = "70000_150000"
    OVER_150000 = "OVER_150000"


class CompanionType(str, enum.Enum):
    SOLO = "SOLO"
    FRIEND = "FRIEND"
    COUPLE = "COUPLE"
    FAMILY = "FAMILY"


class ThemeTag(str, enum.Enum):
    FOOD = "FOOD"
    CAFE = "CAFE"
    BAR = "BAR"
    BOARD_GAME = "BOARD_GAME"
    KARAOKE = "KARAOKE"
    ARCADE = "ARCADE"
    PARK = "PARK"
    CULTURE = "CULTURE"
    SHOPPING = "SHOPPING"
    NIGHT_VIEW = "NIGHT_VIEW"
    MOVIE = "MOVIE"
    ACTIVITY = "ACTIVITY"


class ServedFrom(str, enum.Enum):
    LLM = "LLM"
    CACHE = "CACHE"


class ReportReason(str, enum.Enum):
    SPAM = "SPAM"
    INAPPROPRIATE = "INAPPROPRIATE"
    WRONG_INFO = "WRONG_INFO"
    OTHER = "OTHER"
