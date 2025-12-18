"""
공통 프롬프트 생성
- 컨텍스트와 질문을 포함한 프롬프트 구성
- Gemini와 로컬 LLM 모두 동일한 포맷 사용
"""
from typing import List, Dict, Any
import re


def build_prompt(
    query: str,
    contexts: List[Dict[str, Any]],
    product_id: int
) -> str:
    """
    RAG 프롬프트 생성
    
    Args:
        query: 사용자 질문
        contexts: 검색된 컨텍스트 리스트
        product_id: 상품 ID
        
    Returns:
        완성된 프롬프트
    """
    # 컨텍스트 포맷팅
    context_text = ""
    if contexts:
        context_text = "\n\n".join([
            f"[{ctx['type']}] {ctx['content']}"
            for ctx in contexts
        ])
    else:
        context_text = "(검색된 관련 정보가 없습니다)"

    # 부정형 질문 힌트 (예: "…할 수 없어?", "안 돼?", "못 해?")
    # 한국어에서 부정형 질문은 의미가 애매해(수사/확인 질문) LLM이 "네, 가능합니다"처럼
    # yes/no를 질문의 부정과 무관하게 출력하는 문제가 자주 발생하므로, 보조 힌트를 제공합니다.
    q = (query or "").strip()
    is_negative_question = bool(
        re.search(r"(없어\?|없나요\?|안\s*돼\?|안되\?|못\s*해\?|못해\?|불가\?|불가능\?)\s*$", q)
    )
    polarity_hint = ""
    if is_negative_question:
        polarity_hint = (
            "주의: 사용자의 질문은 부정형(예: '…할 수 없어?')입니다. "
            "가능/불가능 판단 자체는 동일하더라도, 답변 첫 문장의 예/아니오를 질문의 부정에 맞게 정합적으로 선택하세요.\n"
        )
    
    # 프롬프트 구성
    # NOTE:
    # - "근거/출처"는 API 응답의 sources로 별도 제공하므로, LLM 답변에는 포함하지 않습니다.
    # - 정보가 부족하더라도 관련된 정보가 있으면 그 범위 안에서 최대한 도움되는 답을 하되,
    #   없는 내용은 추측/단정하지 않도록 합니다.
    prompt = f"""당신은 아래 '상품 정보'만 근거로 답변하는 쇼핑 도우미입니다.

규칙:
- '상품 정보'에 없는 내용은 추측/단정하지 마세요.
- 질문과 직접적으로 연결되는 근거가 없으면, 아는 범위까지만 설명하고 "정확한 확인은 상품 상세 페이지의 Q&A에 문의해주세요."라고 안내하세요.
- 질문이 가능/불가능 여부를 묻는 형태라면, 답변 첫 문장에서 예/아니오를 질문의 긍/부정에 맞게 정합적으로 선택하세요.
  - 긍정형 질문(예: "사용할 수 있어?") + 가능 → "네, …할 수 있습니다."
  - 부정형 질문(예: "사용할 수 없어?") + 가능 → "아니요, …할 수 있습니다."
  - 긍정형 질문 + 불가능 → "아니요, …할 수 없습니다."
  - 부정형 질문 + 불가능 → "네, …할 수 없습니다."
- 부정형 질문의 의도가 애매하면(수사/확인 질문 가능) 한 문장으로 되물어 확인한 뒤 답하세요.
- 아래 규칙/형식 문구를 설명하거나 복사하지 말고, 최종 답변만 출력하세요.
- 답변에는 "근거:", "출처:", 따옴표 인용, 타입 표기(description/review/qna)를 절대 포함하지 마세요.
- 답변은 최대 5줄 이내로 간결하게 작성하세요.

상품 정보:
{context_text}

질문:
{polarity_hint}{query}

최종 답변:"""
    
    return prompt


def build_prompt_with_source_selection(
    query: str,
    contexts: List[Dict[str, Any]],
    product_id: int
) -> str:
    """
    RAG 프롬프트(소스 사용 여부 선택 포함)

    - LLM이 "실제로 답변에 사용한 컨텍스트(source_id)"만 반환하도록 강제합니다.
    - 최종 출력은 JSON 단일 오브젝트여야 합니다.

    Returns:
        JSON 문자열만 출력하도록 설계된 프롬프트
    """
    # 컨텍스트 포맷팅 (각 컨텍스트에 source_id를 부여하여 선택 가능하게 함)
    if contexts:
        parts = []
        for ctx in contexts:
            sid = str(ctx.get("source_id") or "")
            ctype = str(ctx.get("type") or "")
            score = float(ctx.get("score", 0.0) or 0.0)
            content = str(ctx.get("content") or "")
            parts.append(
                "=== SOURCE ===\n"
                f"source_id: {sid}\n"
                f"type: {ctype}\n"
                f"score: {score:.4f}\n"
                "content:\n"
                f"{content}\n"
                "=== /SOURCE ==="
            )
        context_text = "\n\n".join(parts)
    else:
        context_text = "(검색된 관련 정보가 없습니다)"

    # 부정형 질문 힌트 (기존 로직 유지)
    q = (query or "").strip()
    is_negative_question = bool(
        re.search(r"(없어\?|없나요\?|안\s*돼\?|안되\?|못\s*해\?|못해\?|불가\?|불가능\?)\s*$", q)
    )
    polarity_hint = ""
    if is_negative_question:
        polarity_hint = (
            "주의: 사용자의 질문은 부정형(예: '…할 수 없어?')입니다. "
            "가능/불가능 판단 자체는 동일하더라도, 답변 첫 문장의 예/아니오를 질문의 부정에 맞게 정합적으로 선택하세요.\n"
        )

    # JSON 출력 강제
    # - answer에는 출처/메타 문구를 넣지 말 것
    # - used_source_ids는 '실제로 답변 근거로 사용한' source_id만 포함 (부분적으로 참고했다면 포함)
    # - 근거가 부족해 Q&A 문의 안내로 끝내는 경우 used_source_ids는 []로 두는 것이 안전
    prompt = f"""당신은 아래 '상품 정보'만 근거로 답변하는 쇼핑 도우미입니다.

규칙:
- '상품 정보'에 없는 내용은 추측/단정하지 마세요.
- 질문과 직접적으로 연결되는 근거가 없으면, 아는 범위까지만 설명하고 "정확한 확인은 상품 상세 페이지의 Q&A에 문의해주세요."라고 안내하세요.
- 질문이 가능/불가능 여부를 묻는 형태라면, 답변 첫 문장에서 예/아니오를 질문의 긍/부정에 맞게 정합적으로 선택하세요.
  - 긍정형 질문(예: "사용할 수 있어?") + 가능 → "네, …할 수 있습니다."
  - 부정형 질문(예: "사용할 수 없어?") + 가능 → "아니요, …할 수 있습니다."
  - 긍정형 질문 + 불가능 → "아니요, …할 수 없습니다."
  - 부정형 질문 + 불가능 → "네, …할 수 없습니다."
- 부정형 질문의 의도가 애매하면(수사/확인 질문 가능) 한 문장으로 되물어 확인한 뒤 답하세요.
- 아래 규칙/형식 문구를 설명하거나 복사하지 말고, 최종 결과(JSON)만 출력하세요.
- answer에는 "근거:", "출처:", 따옴표 인용, 타입 표기(description/review/qna), source_id를 절대 포함하지 마세요.
- answer는 최대 5줄 이내로 간결하게 작성하세요.

출력 형식(중요):
- 반드시 아래 JSON 오브젝트만 출력하세요. (코드펜스 ``` 금지, 추가 텍스트 금지)
- used_source_ids는 문자열 배열이며, 아래 '상품 정보'에 있는 source_id 값만 넣을 수 있습니다.
- used_source_ids에는 "실제로 답변 근거로 사용한" 소스만 넣으세요. 검색만 되었지만 답변에 쓰지 않았으면 넣지 마세요.

{{"answer":"...","used_source_ids":["..."]}}

상품 정보:
{context_text}

질문:
{polarity_hint}{query}

JSON:"""
    return prompt


def build_simple_prompt(query: str) -> str:
    """
    컨텍스트 없이 단순 질문에 대한 프롬프트
    (fallback용)
    """
    prompt = f"""당신은 친절한 쇼핑 도우미입니다. 다음 질문에 답변해주세요.

질문: {query}

답변:"""
    
    return prompt

