from __future__ import annotations

from typing import List, Optional, Dict, Any
import re

from .constants import QUERY_STOP_TOKENS


def _question_match_score(query: str, question: str) -> int:
    """사용자 질문과 FAQ 질문 간의 간단 매칭 점수."""
    if not query or not question:
        return 0

    q = query.lower()
    t = question.lower()

    tokens = re.findall(r"[0-9a-z가-힣]{2,}", q)
    if not tokens:
        return 0

    tokens = [tok for tok in tokens if tok not in QUERY_STOP_TOKENS]
    if not tokens:
        return 0

    return sum(1 for tok in tokens if tok in t)


def _get_default_questions(product_id: int) -> List[str]:
    """상품별 기본 FAQ 질문"""
    from db.repository import get_product_by_id

    product: Optional[Dict[str, Any]] = get_product_by_id(product_id)
    if not product:
        return [
            "이 제품의 핵심 특징을 알려주세요",
            "구성품/옵션은 어떻게 되나요?",
            "사이즈/무게는 어느 정도인가요?",
            "사용/관리 방법을 알려주세요",
            "배송/교환/반품은 어떻게 되나요?",
        ]

    product_name = product.get("name", "제품")

    # 제품명 기반 FAQ 질문
    if "이불" in product_name:
        return [
            f"{product_name} 소재는 무엇인가요?",
            f"{product_name} 세탁/관리 방법은 어떻게 되나요?",
            f"{product_name} 사이즈/구성 옵션을 알려주세요",
            f"{product_name} 두께감/계절감은 어떤가요?",
            "배송/교환/반품은 어떻게 되나요?",
        ]
    if "쌀국수" in product_name:
        return [
            f"{product_name} 조리 방법을 알려주세요",
            f"{product_name} 매운 정도가 어떤가요?",
            f"{product_name} 보관/유통기한은 어떻게 되나요?",
            f"{product_name} 1인분 기준 양이 어느 정도인가요?",
            "배송/교환/반품은 어떻게 되나요?",
        ]
    return [
        f"{product_name} 핵심 특징을 알려주세요",
        f"{product_name} 구성품/옵션은 어떻게 되나요?",
        f"{product_name} 사이즈/무게는 어느 정도인가요?",
        f"{product_name} 사용/관리 방법을 알려주세요",
        "배송/교환/반품은 어떻게 되나요?",
    ]


def suggest_related_questions(
    user_query: str,
    product_id: int,
    asked_questions: List[str],
    top_k: int = 2,
) -> List[str]:
    """사용자 질문과 관련된 FAQ 질문 추천"""
    defaults = _get_default_questions(product_id)
    candidates = [q for q in defaults if q not in asked_questions]
    if not candidates:
        return []

    scored = [
        (question, _question_match_score(user_query, question), idx)
        for idx, question in enumerate(candidates)
    ]

    scored.sort(key=lambda x: (-x[1], x[2]))
    suggested = [q for q, _, _ in scored[:top_k]]
    return suggested

