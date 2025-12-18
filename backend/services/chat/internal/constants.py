from __future__ import annotations

from typing import List, Set
import os


# similarity는 1/(1+distance)로 정규화되어 보통 0.01~0.2 사이로 분포할 수 있습니다.
# 너무 높게 잡으면 "관련 컨텍스트가 있음에도" 폴백이 발생합니다.
MIN_CONTEXT_SCORE = 0.05  # 너무 약한 컨텍스트는 환각을 유발하기 쉬움
DIRECT_QNA_MIN_SCORE = 0.07  # QnA는 원문 답변을 그대로 쓰는 편이 정확/빠름
DIRECT_QNA_STRONG_SCORE = 0.18  # 매우 높은 점수면 직접 반환 허용


def load_csv_env(name: str, default: List[str]) -> List[str]:
    """
    콤마(,)로 구분된 환경변수를 리스트로 파싱합니다.
    - 운영 중 튜닝을 위해 룰/키워드를 코드 하드코딩으로 두지 않습니다.
    """
    raw = os.getenv(name)
    if not raw:
        return default
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


# 키워드 휴리스틱 설정(운영 중 조정 가능)
QUERY_STOP_TOKENS: Set[str] = set(
    load_csv_env(
        "CHAT_QUERY_STOP_TOKENS",
        [
            "이",
            "그",
            "저",
            "것",
            "거",
            "수",
            "좀",
            "정도",
            "관련",
            "가능",
            "여부",
            "있나",
            "있나요",
            "있어",
            "있어요",
            "되나요",
            "되나",
            "인가",
            "인가요",
            "어떻게",
            "왜",
            "무엇",
            "뭐",
            "어떤",
            "얼마",
            "얼마나",
            "해주세요",
            "알려줘",
            # 너무 일반적이라 단독 키워드로는 신뢰하기 어려움
            "기능",
        ],
    )
)


DIRECT_QNA_ENABLED = os.getenv("CHAT_DIRECT_QNA_ENABLED", "false").lower() in [
    "1",
    "true",
    "yes",
    "y",
    "on",
]

