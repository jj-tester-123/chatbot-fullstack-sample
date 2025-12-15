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
    # - "근거/출처"는 API 응답의 sources로 별도 제공하므로, LLM 답변에는 포함하지 않습니다.
    # - 정보가 부족하더라도 관련된 정보가 있으면 그 범위 안에서 최대한 도움되는 답을 하되,
    #   없는 내용은 추측/단정하지 않도록 합니다.
    prompt = f"""당신은 아래 '상품 정보'만 근거로 답변하는 쇼핑 도우미입니다.

규칙:
- '상품 정보'에 없는 내용은 추측/단정하지 마세요.
- 질문과 직접적으로 연결되는 근거가 없으면, 아는 범위까지만 설명하고 "정확한 확인은 상품 상세 페이지의 Q&A에 문의해주세요."라고 안내하세요.
- 아래 규칙/형식 문구를 설명하거나 복사하지 말고, 최종 답변만 출력하세요.
- 답변에는 "근거:", "출처:", 따옴표 인용, 타입 표기(description/review/qna)를 절대 포함하지 마세요.
- 답변은 최대 5줄 이내로 간결하게 작성하세요.

상품 정보:
{context_text}

질문:
{query}

최종 답변:"""
    
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

