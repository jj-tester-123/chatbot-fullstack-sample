"""
챗봇 API 라우터
- POST /chat: RAG + LLM 기반 질의응답
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from rag.retriever import retrieve_context
from llm.engine import generate_answer, get_available_engines
from llm.prompt import build_prompt
from llm.local_engine import init_local_model, is_local_model_available

logger = logging.getLogger(__name__)

router = APIRouter()

# similarity는 1/(1+distance)로 정규화되어 보통 0.01~0.2 사이로 분포할 수 있습니다.
# 너무 높게 잡으면 "관련 컨텍스트가 있음에도" 폴백이 발생합니다.
_MIN_CONTEXT_SCORE = 0.05  # 너무 약한 컨텍스트는 환각을 유발하기 쉬움
_DIRECT_QNA_MIN_SCORE = 0.07  # QnA는 원문 답변을 그대로 쓰는 편이 정확/빠름


def _no_rag_fallback_answer() -> str:
    """
    RAG로 근거를 찾지 못했을 때의 폴백 문구.
    - 답변을 지어내지 않도록 즉시 종료합니다.
    - 사용자가 Q&A를 남기도록 유도합니다.
    """
    return (
        "제공된 상품 정보에서 답변할 근거를 찾지 못해 정확히 안내드리기 어렵습니다. "
        "상품 상세 페이지의 Q&A에 질문을 남겨주시면 확인 후 답변드릴게요."
    )


def _extract_qna_answer(content: str) -> Optional[str]:
    """product_texts.qna의 'Q: ...\\nA: ...' 포맷에서 A만 추출"""
    if not content or "A:" not in content:
        return None
    answer = content.split("A:", 1)[1].strip()
    return answer or None


def _looks_like_template_garbage(answer: str) -> bool:
    """
    로컬 LLM이 프롬프트의 템플릿/설명 문구를 복사해버린 경우를 탐지.
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


def _summarize_key_features_from_contexts(contexts: List[dict]) -> str:
    """
    LLM이 이상한 답을 내놓을 때, RAG 컨텍스트만으로 규칙 기반 요약을 생성.
    - 우선 description 컨텍스트를 사용
    - 대표 스펙(블루투스/ANC/IPX/배터리)을 뽑아 bullet로 정리
    """
    import re

    if not contexts:
        return _no_rag_fallback_answer()

    desc = next((c for c in contexts if c.get("type") == "description"), None)
    text = (desc or max(contexts, key=lambda c: c.get("score", 0.0))).get("content", "") or ""

    features: List[str] = []

    m = re.search(r"블루투스\s*([0-9]+(?:\.[0-9]+)?)", text)
    if m:
        features.append(f"블루투스 {m.group(1)} 지원")
    if "낮은 지연" in text or "지연시간" in text:
        features.append("낮은 지연시간(끊김/지연 개선)")

    m = re.search(r"(?:노이즈\s*캔슬링|ANC)[^0-9]{0,20}([0-9]{1,3})\s*dB", text, flags=re.IGNORECASE)
    if m:
        features.append(f"액티브 노이즈 캔슬링(최대 {m.group(1)}dB)")

    m = re.search(r"IPX\s*([0-9])", text, flags=re.IGNORECASE)
    if m:
        features.append(f"방수 등급: IPX{m.group(1)}")

    m1 = re.search(r"최대\s*([0-9]{1,2})\s*시간", text)
    m2 = re.search(r"총\s*([0-9]{1,3})\s*시간", text)
    if m1 and m2:
        features.append(f"배터리: 단독 최대 {m1.group(1)}시간 / 케이스 포함 총 {m2.group(1)}시간")
    elif m1:
        features.append(f"배터리: 단독 최대 {m1.group(1)}시간")

    if not features:
        # fallback: description의 앞 문장 1~2개만 발췌
        cleaned = " ".join(text.split())
        return cleaned[:180].strip() if cleaned else _no_rag_fallback_answer()

    bullet = "\n".join([f"- {f}" for f in features[:5]])
    return f"주요 특징은 아래와 같습니다.\n{bullet}"

class ChatRequest(BaseModel):
    """챗봇 요청"""
    query: str = Field(..., description="사용자 질문")
    product_id: int = Field(..., description="상품 ID (검색 범위 제한)")
    engine: str = Field(default="gemini", description="LLM 엔진 선택: 'gemini' 또는 'local'")


class ContextSource(BaseModel):
    """검색된 컨텍스트 소스"""
    content: str
    type: str  # description, review, qna
    score: float


class ChatResponse(BaseModel):
    """챗봇 응답"""
    answer: str
    sources: List[ContextSource]
    engine: str
    product_id: int


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    RAG + LLM 기반 챗봇 응답
    
    1. product_id로 범위를 제한하여 ChromaDB에서 관련 컨텍스트 검색
    2. 검색된 컨텍스트를 prompt에 포함
    3. 선택된 엔진(gemini/local)으로 LLM 응답 생성
    """
    try:
        # 엔진 검증
        if request.engine not in ["gemini", "local"]:
            raise HTTPException(
                status_code=400,
                detail="engine은 'gemini' 또는 'local'이어야 합니다."
            )

        # 엔진 가용성 확인 (폴백 금지: 요청한 엔진을 그대로 사용)
        available = get_available_engines()
        selected_engine = request.engine
        if selected_engine == "local" and not available.get("local", False):
            # 서버 시작 시 로컬 로드가 실패/지연될 수 있으므로, 요청 시 한 번 더 초기화를 시도합니다.
            init_local_model()
            if not is_local_model_available():
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "현재 local 엔진을 사용할 수 없습니다. (로컬 모델 로드 실패/미초기화) "
                        "서버 시작 로그의 local_engine 오류를 확인하세요. "
                        "방금 transformers/tokenizers를 업그레이드했다면, 패키지 교체는 프로세스 재시작이 필요합니다."
                    ),
                )
            available["local"] = True
        if selected_engine == "gemini" and not available.get("gemini", False):
            raise HTTPException(
                status_code=503,
                detail=(
                    "현재 gemini 엔진을 사용할 수 없습니다. (API 키/패키지 설정 확인) "
                    "요청 엔진 폴백은 비활성화되어 있습니다."
                ),
            )
        
        logger.info(f"질문: {request.query}")
        logger.info(f"상품 ID: {request.product_id}, 엔진: {selected_engine}")
        
        # 1. RAG: 관련 컨텍스트 검색 (product_id로 범위 제한)
        logger.info("컨텍스트 검색 중...")
        contexts = retrieve_context(
            query=request.query,
            product_id=request.product_id,
            top_k=5
        )
        
        if not contexts:
            logger.warning("검색된 컨텍스트가 없습니다. LLM 호출 없이 폴백 응답 반환")
            return ChatResponse(
                answer=_no_rag_fallback_answer(),
                sources=[],
                engine=selected_engine,
                product_id=request.product_id
            )

        # 컨텍스트가 있더라도 유사도가 지나치게 낮으면, 잘못된 추론 답변이 나올 수 있어 가드합니다.
        best_score = max((ctx.get("score", 0.0) for ctx in contexts), default=0.0)
        if best_score < _MIN_CONTEXT_SCORE:
            logger.warning(
                f"컨텍스트 유사도 낮음(best_score={best_score:.3f}). LLM 호출 없이 폴백 응답 반환"
            )
            return ChatResponse(
                answer=_no_rag_fallback_answer(),
                sources=[
                    ContextSource(
                        content=ctx["content"],
                        type=ctx["type"],
                        score=ctx["score"]
                    )
                    for ctx in contexts
                ],
                engine=selected_engine,
                product_id=request.product_id
            )

        # QnA 문서가 가장 유력하면 LLM을 거치지 않고 원문 답변을 바로 반환합니다.
        # - 로컬 LLM은 느릴 수 있고, 환각/요약 실수 여지가 있습니다.
        best_ctx = max(contexts, key=lambda c: c.get("score", 0.0))
        if best_ctx.get("type") == "qna" and best_ctx.get("score", 0.0) >= _DIRECT_QNA_MIN_SCORE:
            direct = _extract_qna_answer(best_ctx.get("content", ""))
            if direct:
                logger.info("QnA 원문 답변을 직접 반환합니다. (LLM 미사용)")
                return ChatResponse(
                    answer=direct,
                    sources=[
                        ContextSource(
                            content=ctx["content"],
                            type=ctx["type"],
                            score=ctx["score"]
                        )
                        for ctx in contexts
                    ],
                    engine=selected_engine,
                    product_id=request.product_id
                )
        
        # 2. Prompt 생성
        prompt = build_prompt(
            query=request.query,
            contexts=contexts,
            product_id=request.product_id
        )
        
        # 3. LLM 응답 생성
        logger.info(f"{selected_engine} 엔진으로 답변 생성 중...")
        answer = await generate_answer(
            prompt=prompt,
            engine=selected_engine
        )

        # 로컬 LLM이 템플릿/설명 문구를 그대로 복사해버리는 경우:
        # - 잘못된/무의미한 답변을 그대로 노출하지 않고,
        # - 답변 불가 + Q&A 문의 안내로 안전하게 종료합니다.
        if _looks_like_template_garbage(answer):
            logger.warning("LLM 출력이 템플릿/메타 문구로 보입니다. Q&A 문의 안내로 폴백합니다.")
            answer = _no_rag_fallback_answer()
        
        # 4. 응답 구성
        sources = [
            ContextSource(
                content=ctx["content"],
                type=ctx["type"],
                score=ctx["score"]
            )
            for ctx in contexts
        ]
        
        logger.info("답변 생성 완료")
        
        return ChatResponse(
            answer=answer,
            sources=sources,
            engine=selected_engine,
            product_id=request.product_id
        )
        
    except Exception as e:
        logger.error(f"챗봇 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"챗봇 처리 중 오류가 발생했습니다: {str(e)}")

