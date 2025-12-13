"""
공통 프롬프트 생성
- 컨텍스트와 질문을 포함한 프롬프트 구성
- Gemini와 로컬 LLM 모두 동일한 포맷 사용
"""
from typing import List, Dict, Any


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
    
    # 프롬프트 구성
    # NOTE:
    # - 로컬 소형 모델은 "형식 예시"를 그대로 복사하는 경향이 있어 플레이스홀더([type] 등)를 제거합니다.
    # - 답변은 "답변 + 근거(짧은 인용 1~3개)"만 출력하도록 강하게 제한합니다.
    prompt = f"""당신은 아래 '상품 정보'만 근거로 답변하는 쇼핑 도우미입니다.

규칙:
- '상품 정보'에 없는 내용은 추측/단정하지 마세요. 특히 최소 사양/조건을 만들어내지 마세요.
- 정보가 부족하면 반드시 다음 문장을 그대로 포함해 답하세요: "제공된 정보로는 정확히 답변드리기 어렵습니다"
- 아래에 적힌 규칙/형식/예시 문장을 설명하거나 그대로 복사하지 말고, 최종 답변만 출력하세요.
- 답변은 최대 5줄 이내로 간결하게 작성하세요.
- 마지막에 근거를 1~3개만 짧게 인용하세요. 근거는 반드시 상품 정보의 문장을 그대로 따옴표로 인용하세요.
- 근거 라인에는 타입을 description/review/qna 중 하나로 표시하세요.

상품 정보:
{context_text}

질문:
{query}

최종 답변(아래 형태로만 출력):
답변: ...
근거:
- (description|review|qna) "..."
"""
    
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

