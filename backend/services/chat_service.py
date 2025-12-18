"""
챗봇 서비스 레이어

- API 라우터에서 비즈니스 로직을 분리합니다.
- 외부 모듈은 `services.chat_service.handle_chat`만 사용합니다.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any, Set
import logging

from fastapi import HTTPException

from rag.retriever import retrieve_context
from llm.engine import generate_answer, get_available_engines
from llm.prompt import build_prompt_with_source_selection

from .chat.internal.constants import (
    MIN_CONTEXT_SCORE,
    DIRECT_QNA_ENABLED,
    DIRECT_QNA_MIN_SCORE,
    DIRECT_QNA_STRONG_SCORE,
)
from .chat.internal.guards import (
    extract_json_object,
    extract_qna_answer,
    extract_qna_question,
    keyword_overlap,
    looks_like_template_garbage,
)
from .chat.internal.responses import build_chat_response, build_no_rag_stop_response, context_to_source
from .chat.internal.suggestions import suggest_related_questions

logger = logging.getLogger(__name__)


def _ensure_engine_available(engine: str) -> str:
    """gemini만 허용하고, 사용 가능 여부를 확인합니다."""
    # 엔진 검증
    if engine != "gemini":
        raise HTTPException(status_code=400, detail="engine은 'gemini'여야 합니다.")

    # 엔진 가용성 확인 (폴백 금지: 요청한 엔진을 그대로 사용)
    available = get_available_engines()
    selected_engine = engine
    if not available.get("gemini", False):
        raise HTTPException(
            status_code=503,
            detail=(
                "현재 gemini 엔진을 사용할 수 없습니다. (API 키/패키지 설정 확인) "
                "요청 엔진 폴백은 비활성화되어 있습니다."
            ),
        )

    return selected_engine


def _retrieve_contexts(query: str, product_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
    """retrieve_context를 래핑합니다."""
    return retrieve_context(query=query, product_id=product_id, top_k=top_k)


def _build_stop_response_if_needed(
    *,
    contexts: List[Dict[str, Any]],
    selected_engine: str,
    product_id: int,
) -> Optional[Dict[str, Any]]:
    """
    컨텍스트가 없거나 약할 때 LLM 호출 없이 즉시 종료할 응답을 생성합니다.
    - stop 응답의 suggested_questions는 빈 리스트로 유지합니다.
    """
    if not contexts:
        logger.warning("검색된 컨텍스트가 없습니다. LLM 호출 없이 폴백 응답 반환")
        return build_no_rag_stop_response(selected_engine=selected_engine, product_id=product_id)

    # 컨텍스트가 있더라도 유사도가 지나치게 낮으면, 잘못된 추론 답변이 나올 수 있어 가드합니다.
    best_score = max((ctx.get("score", 0.0) for ctx in contexts), default=0.0)
    if best_score < MIN_CONTEXT_SCORE:
        logger.warning(
            "컨텍스트 유사도 낮음(best_score=%.3f). LLM 호출 없이 폴백 응답 반환",
            best_score,
        )
        # 유사도가 낮은 컨텍스트는 '근거'로 제시하면 오히려 혼란을 유발하므로 숨깁니다.
        return build_no_rag_stop_response(selected_engine=selected_engine, product_id=product_id)

    return None


def _try_direct_qna_answer(
    query: str,
    contexts: List[Dict[str, Any]],
    selected_engine: str,
    product_id: int,
) -> Optional[Dict[str, Any]]:
    """
    (옵션) QnA direct return.
    env CHAT_DIRECT_QNA_ENABLED가 켜져있고 조건 충족 시 LLM 호출 없이 QnA 답변을 반환합니다.
    """
    # QnA 문서가 가장 유력하면 LLM을 거치지 않고 원문 답변을 바로 반환합니다.
    # NOTE: "QnA 직접 반환"은 질문 의도를 무시하는 단답을 만들기 쉬워 기본 비활성화합니다.
    # 필요하면 CHAT_DIRECT_QNA_ENABLED=true 로 켤 수 있습니다.
    if not DIRECT_QNA_ENABLED:
        return None

    if not contexts:
        return None

    best_ctx = max(contexts, key=lambda c: c.get("score", 0.0))
    if not (
        best_ctx.get("type") == "qna"
        and float(best_ctx.get("score", 0.0) or 0.0) >= DIRECT_QNA_MIN_SCORE
    ):
        return None

    qna_content = best_ctx.get("content", "") or ""
    qna_question = extract_qna_question(qna_content) or ""
    score = float(best_ctx.get("score", 0.0) or 0.0)

    # 직접 반환은 매우 보수적으로: 질문 키워드가 QnA 질문(Q:)에 실제로 겹칠 때만 허용합니다.
    # (답변(A:) 매칭까지 허용하면 "질문 의도 무시" 단답이 더 자주 발생합니다.)
    if not (keyword_overlap(query, qna_question) and score >= DIRECT_QNA_STRONG_SCORE):
        return None

    direct = extract_qna_answer(qna_content)
    if not direct:
        return None

    logger.info("QnA 원문 답변을 직접 반환합니다. (LLM 미사용)")
    return build_chat_response(
        answer=direct,
        sources=[context_to_source(best_ctx)],
        selected_engine=selected_engine,
        product_id=product_id,
        suggested_questions=[],
    )


def _build_prompt(query: str, contexts: List[Dict[str, Any]], product_id: int) -> str:
    """build_prompt_with_source_selection 호출을 래핑합니다."""
    return build_prompt_with_source_selection(
        query=query,
        contexts=contexts,
        product_id=product_id,
    )


async def _run_llm(prompt: str, selected_engine: str) -> str:
    """generate_answer 호출을 래핑합니다."""
    logger.info("%s 엔진으로 답변 생성 중...", selected_engine)
    return await generate_answer(prompt=prompt, engine=selected_engine)


def _parse_llm_output(raw_text: str) -> tuple[str, List[str]]:
    """
    LLM 출력(JSON)에서 answer + 실제 사용한 source_id 목록을 추출합니다.
    - JSON 파싱 실패 시: used_source_ids는 []로 반환하고, sources는 안전하게 숨깁니다.
    """
    answer = raw_text
    used_source_ids: List[str] = []

    parsed = extract_json_object(raw_text)
    if parsed is not None:
        parsed_answer = parsed.get("answer")
        parsed_used = parsed.get("used_source_ids")
        if isinstance(parsed_answer, str) and parsed_answer.strip():
            answer = parsed_answer.strip()
        if isinstance(parsed_used, list):
            used_source_ids = [str(x) for x in parsed_used if str(x).strip()]
        return answer, used_source_ids

    # JSON 파싱 실패 시: sources는 안전하게 숨김(검색만 된 근거를 "참고한 정보"로 보여주지 않기 위함)
    logger.warning("LLM JSON 파싱 실패: sources를 숨깁니다.")
    return answer, used_source_ids


def _filter_sources_by_used_ids(
    contexts: List[Dict[str, Any]],
    used_source_ids: List[str],
) -> List[Dict[str, Any]]:
    """used_source_ids에 포함된 source_id만 sources로 변환합니다(dict 형식 유지)."""
    used_set: Set[str] = set(used_source_ids)
    used_contexts = [ctx for ctx in contexts if str(ctx.get("source_id") or "") in used_set]
    return [context_to_source(ctx) for ctx in used_contexts]


def _suggest_questions(
    query: str,
    product_id: int,
    conversation_history: List[str],
    top_k: int = 2,
) -> List[str]:
    """기존 추천 질문 로직을 래핑합니다."""
    return suggest_related_questions(
        user_query=query,
        product_id=product_id,
        asked_questions=conversation_history,
        top_k=top_k,
    )


async def handle_chat(
    *,
    query: str,
    product_id: int,
    engine: str,
    conversation_history: List[str],
) -> Dict[str, Any]:
    """
    챗봇 요청 처리(서비스 레이어).

    반환값은 API의 ChatResponse와 동일한 shape의 dict입니다.
    (라우터는 이 dict를 그대로 반환하거나, Pydantic 모델로 감싸서 반환할 수 있습니다.)
    """
    try:
        # 0. 사용 가능 여부 확인
        selected_engine = _ensure_engine_available(engine)

        logger.info("질문: %s", query)
        logger.info("상품 ID: %s, 엔진: %s", product_id, selected_engine)

        # 1. 근거 검색 (product_id로 범위 제한)
        logger.info("컨텍스트 검색 중...")
        contexts = _retrieve_contexts(query=query, product_id=product_id, top_k=5)

        # 2. 근거 부족 시 즉시 종료(안내 응답)
        stop_response = _build_stop_response_if_needed(
            contexts=contexts,
            selected_engine=selected_engine,
            product_id=product_id,
        )
        if stop_response is not None:
            return stop_response

        # 3. (옵션) QnA direct return
        direct_response = _try_direct_qna_answer(
            query=query,
            contexts=contexts,
            selected_engine=selected_engine,
            product_id=product_id,
        )
        if direct_response is not None:
            return direct_response

        # 4. 프롬프트 생성
        prompt = _build_prompt(query=query, contexts=contexts, product_id=product_id)

        # 5. LLM 호출
        raw_text = await _run_llm(prompt=prompt, selected_engine=selected_engine)

        # 6. LLM 출력 파싱(answer + used_source_ids)
        answer, used_source_ids = _parse_llm_output(raw_text)

        # 7. 템플릿 가드
        if looks_like_template_garbage(answer):
            logger.warning("LLM 출력이 템플릿/메타 문구로 보입니다. Q&A 문의 안내로 폴백합니다.")
            return build_no_rag_stop_response(selected_engine=selected_engine, product_id=product_id)

        # 8. used_source_ids 기반 sources 필터링
        sources = _filter_sources_by_used_ids(contexts, used_source_ids)

        # 9. 추천 질문 생성
        suggested = _suggest_questions(
            query=query,
            product_id=product_id,
            conversation_history=conversation_history,
            top_k=2,
        )

        logger.info("답변 생성 완료")

        return build_chat_response(
            answer=answer,
            sources=sources,
            selected_engine=selected_engine,
            product_id=product_id,
            suggested_questions=suggested,
        )

    except HTTPException:
        raise
    except Exception:
        # 보안: 내부 예외 메시지/스택을 클라이언트에 그대로 노출하지 않습니다.
        logger.exception("챗봇 처리 중 오류")
        raise HTTPException(status_code=500, detail="챗봇 처리 중 오류가 발생했습니다.")


__all__ = ["handle_chat"]
