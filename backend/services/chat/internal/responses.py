from __future__ import annotations

from typing import Any, Dict, List


def no_rag_fallback_answer() -> str:
    """
    RAG로 근거를 찾지 못했을 때의 폴백 문구.
    - 답변을 지어내지 않도록 즉시 종료합니다.
    - 사용자가 Q&A를 남기도록 유도합니다.
    """
    return (
        "제공된 상품 정보에서 답변할 근거를 찾지 못해 정확히 안내드리기 어렵습니다. "
        "상품 상세 페이지의 Q&A에 질문을 남겨주시면 확인 후 답변드릴게요."
    )


def build_chat_response(
    *,
    answer: str,
    sources: List[Dict[str, Any]],
    selected_engine: str,
    product_id: int,
    suggested_questions: List[str],
) -> Dict[str, Any]:
    """API ChatResponse와 동일한 shape의 dict를 생성합니다."""
    return {
        "answer": answer,
        "sources": sources,
        "engine": selected_engine,
        "product_id": product_id,
        "suggested_questions": suggested_questions,
    }


def context_to_source(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """retriever context를 응답 sources 형식으로 변환합니다."""
    return {
        "source_id": str(ctx.get("source_id") or ""),
        "content": ctx.get("content", "") or "",
        "type": ctx.get("type", "") or "",
        "score": float(ctx.get("score", 0.0) or 0.0),
    }


def build_no_rag_stop_response(*, selected_engine: str, product_id: int) -> Dict[str, Any]:
    """컨텍스트 부족 시 즉시 종료 응답(suggested_questions=[] 고정)."""
    return build_chat_response(
        answer=no_rag_fallback_answer(),
        sources=[],
        selected_engine=selected_engine,
        product_id=product_id,
        suggested_questions=[],
    )

