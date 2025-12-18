from __future__ import annotations

from typing import Optional
import json
import re

from .constants import QUERY_STOP_TOKENS


def extract_qna_answer(content: str) -> Optional[str]:
    """product_texts.qna의 'Q: ...\\nA: ...' 포맷에서 A만 추출"""
    if not content or "A:" not in content:
        return None
    answer = content.split("A:", 1)[1].strip()
    return answer or None


def extract_qna_question(content: str) -> Optional[str]:
    """product_texts.qna의 'Q: ...\\nA: ...' 포맷에서 Q만 추출"""
    if not content or "Q:" not in content:
        return None
    q_part = content.split("Q:", 1)[1]
    if "A:" in q_part:
        q_part = q_part.split("A:", 1)[0]
    q = q_part.strip()
    return q or None


def keyword_overlap(query: str, text: str) -> bool:
    """
    간단 키워드 오버랩 휴리스틱.
    - 임베딩이 과하게 매칭되어 엉뚱한 QnA가 top으로 오는 경우를 막기 위한 안전장치입니다.
    """
    if not query or not text:
        return False

    q = query.lower()
    t = text.lower()

    # 2글자 이상(한글/영문/숫자) 토큰만 사용
    tokens = re.findall(r"[0-9a-z가-힣]{2,}", q)
    if not tokens:
        return False

    tokens = [tok for tok in tokens if tok not in QUERY_STOP_TOKENS]
    if not tokens:
        return False

    return any(tok in t for tok in tokens)


def looks_like_template_garbage(answer: str) -> bool:
    """
    LLM이 프롬프트의 템플릿/설명 문구를 복사해버린 경우를 탐지.
    (예: [type] 반복, '답변 내용에 포함된 정보' 같은 메타 설명 반복 등)
    """
    if not answer:
        return True
    lowered = answer.lower()
    red_flags = [
        "[type]",
        "답변 내용에 포함된 정보",
        "=== 답변",
        "=== 질문",
        "q:",
        "a:",
        "답변 형식",
        "(description|review|qna)",
        "description|review|qna",
    ]
    hits = sum(1 for f in red_flags if f in lowered)
    if hits >= 2:
        return True
    # 같은 문장 반복(간단 휴리스틱)
    if answer.count("답변 내용에 포함된 정보") >= 2:
        return True
    return False


def extract_json_object(text: str) -> Optional[dict]:
    """
    LLM 출력에서 JSON 오브젝트를 최대한 안전하게 추출합니다.
    - 코드펜스가 섞여도 제거 시도
    - 앞뒤 잡문이 있어도 첫 '{' ~ 마지막 '}' 범위 파싱 시도
    """
    if not text:
        return None
    s = text.strip()

    # 코드펜스 제거 (```json ... ```)
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()

    # 1차: 전체를 JSON으로 파싱
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    # 2차: 첫 { ~ 마지막 }만 파싱
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = s[start : end + 1]
    try:
        obj = json.loads(candidate)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None

