"""
챗봇 API 라우터
- POST /chat: RAG + LLM 기반 질의응답
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
import re
import os

from rag.retriever import retrieve_context
from llm.engine import generate_answer, get_available_engines
from llm.prompt import build_prompt

logger = logging.getLogger(__name__)

router = APIRouter()

# similarity는 1/(1+distance)로 정규화되어 보통 0.01~0.2 사이로 분포할 수 있습니다.
# 너무 높게 잡으면 "관련 컨텍스트가 있음에도" 폴백이 발생합니다.
_MIN_CONTEXT_SCORE = 0.05  # 너무 약한 컨텍스트는 환각을 유발하기 쉬움
_DIRECT_QNA_MIN_SCORE = 0.07  # QnA는 원문 답변을 그대로 쓰는 편이 정확/빠름
_DIRECT_QNA_STRONG_SCORE = 0.18  # 매우 높은 점수면 직접 반환 허용


def _load_csv_env(name: str, default: List[str]) -> List[str]:
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
_QUERY_STOP_TOKENS = set(
    _load_csv_env(
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

_DIRECT_QNA_ENABLED = os.getenv("CHAT_DIRECT_QNA_ENABLED", "false").lower() in [
    "1",
    "true",
    "yes",
    "y",
    "on",
]


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


def _extract_qna_question(content: str) -> Optional[str]:
    """product_texts.qna의 'Q: ...\\nA: ...' 포맷에서 Q만 추출"""
    if not content or "Q:" not in content:
        return None
    q_part = content.split("Q:", 1)[1]
    if "A:" in q_part:
        q_part = q_part.split("A:", 1)[0]
    q = q_part.strip()
    return q or None


def _keyword_overlap(query: str, text: str) -> bool:
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

    tokens = [tok for tok in tokens if tok not in _QUERY_STOP_TOKENS]
    if not tokens:
        return False

    return any(tok in t for tok in tokens)


def _question_match_score(query: str, question: str) -> int:
    """사용자 질문과 FAQ 질문 간의 간단 매칭 점수."""
    if not query or not question:
        return 0

    q = query.lower()
    t = question.lower()

    tokens = re.findall(r"[0-9a-z가-힣]{2,}", q)
    if not tokens:
        return 0

    tokens = [tok for tok in tokens if tok not in _QUERY_STOP_TOKENS]
    if not tokens:
        return 0

    return sum(1 for tok in tokens if tok in t)


def _looks_like_template_garbage(answer: str) -> bool:
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


def _get_default_questions(product_id: int) -> List[str]:
    """상품별 기본 FAQ 질문"""
    from db.repository import get_product_by_id

    product = get_product_by_id(product_id)
    if not product:
        return [
            "이 제품의 핵심 특징을 알려주세요",
            "구성품/옵션은 어떻게 되나요?",
            "사이즈/무게는 어느 정도인가요?",
            "사용/관리 방법을 알려주세요",
            "배송/교환/반품은 어떻게 되나요?"
        ]

    product_name = product.get("name", "제품")

    # 제품명 기반 FAQ 질문
    if "이불" in product_name:
        return [
            f"{product_name} 소재는 무엇인가요?",
            f"{product_name} 세탁/관리 방법은 어떻게 되나요?",
            f"{product_name} 사이즈/구성 옵션을 알려주세요",
            f"{product_name} 두께감/계절감은 어떤가요?",
            "배송/교환/반품은 어떻게 되나요?"
        ]
    elif "쌀국수" in product_name:
        return [
            f"{product_name} 조리 방법을 알려주세요",
            f"{product_name} 매운 정도가 어떤가요?",
            f"{product_name} 보관/유통기한은 어떻게 되나요?",
            f"{product_name} 1인분 기준 양이 어느 정도인가요?",
            "배송/교환/반품은 어떻게 되나요?"
        ]
    else:
        return [
            f"{product_name} 핵심 특징을 알려주세요",
            f"{product_name} 구성품/옵션은 어떻게 되나요?",
            f"{product_name} 사이즈/무게는 어느 정도인가요?",
            f"{product_name} 사용/관리 방법을 알려주세요",
            "배송/교환/반품은 어떻게 되나요?"
        ]


def _suggest_related_questions(
    user_query: str,
    product_id: int,
    asked_questions: List[str],
    top_k: int = 2
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


class ChatRequest(BaseModel):
    """챗봇 요청"""
    query: str = Field(..., description="사용자 질문")
    product_id: int = Field(..., description="상품 ID (검색 범위 제한)")
    engine: str = Field(default="gemini", description="LLM 엔진 선택: 'gemini'")
    conversation_history: List[str] = Field(
        default=[],
        description="이미 물어본 질문 리스트 (중복 방지용)"
    )


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
    suggested_questions: List[str] = []


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    RAG + LLM 기반 챗봇 응답
    
    1. product_id로 범위를 제한하여 ChromaDB에서 관련 컨텍스트 검색
    2. 검색된 컨텍스트를 prompt에 포함
    3. 선택된 엔진(gemini)으로 LLM 응답 생성
    """
    try:
        # 엔진 검증
        if request.engine != "gemini":
            raise HTTPException(
                status_code=400,
                detail="engine은 'gemini'여야 합니다."
            )

        # 엔진 가용성 확인 (폴백 금지: 요청한 엔진을 그대로 사용)
        available = get_available_engines()
        selected_engine = request.engine
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
                # 유사도가 낮은 컨텍스트는 '근거'로 제시하면 오히려 혼란을 유발하므로 숨깁니다.
                sources=[],
                engine=selected_engine,
                product_id=request.product_id
            )

        # QnA 문서가 가장 유력하면 LLM을 거치지 않고 원문 답변을 바로 반환합니다.
        # NOTE: "QnA 직접 반환"은 질문 의도를 무시하는 단답을 만들기 쉬워 기본 비활성화합니다.
        # 필요하면 CHAT_DIRECT_QNA_ENABLED=true 로 켤 수 있습니다.
        if _DIRECT_QNA_ENABLED:
            best_ctx = max(contexts, key=lambda c: c.get("score", 0.0))
            if best_ctx.get("type") == "qna" and float(best_ctx.get("score", 0.0) or 0.0) >= _DIRECT_QNA_MIN_SCORE:
                qna_content = best_ctx.get("content", "") or ""
                qna_question = _extract_qna_question(qna_content) or ""
                score = float(best_ctx.get("score", 0.0) or 0.0)

                # 직접 반환은 매우 보수적으로: 질문 키워드가 QnA 질문(Q:)에 실제로 겹칠 때만 허용합니다.
                # (답변(A:) 매칭까지 허용하면 "질문 의도 무시" 단답이 더 자주 발생합니다.)
                if _keyword_overlap(request.query, qna_question) and score >= _DIRECT_QNA_STRONG_SCORE:
                    direct = _extract_qna_answer(qna_content)
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

        # LLM이 템플릿/설명 문구를 그대로 복사해버리는 경우:
        # - 잘못된/무의미한 답변을 그대로 노출하지 않고,
        # - 답변 불가 + Q&A 문의 안내로 안전하게 종료합니다.
        if _looks_like_template_garbage(answer):
            logger.warning("LLM 출력이 템플릿/메타 문구로 보입니다. Q&A 문의 안내로 폴백합니다.")
            return ChatResponse(
                answer=_no_rag_fallback_answer(),
                sources=[],
                engine=selected_engine,
                product_id=request.product_id
            )
        
        # 4. 응답 구성
        sources = [
            ContextSource(
                content=ctx["content"],
                type=ctx["type"],
                score=ctx["score"]
            )
            for ctx in contexts
        ]

        # 5. 추천 질문 생성
        suggested = _suggest_related_questions(
            user_query=request.query,
            product_id=request.product_id,
            asked_questions=request.conversation_history,
            top_k=2
        )

        logger.info("답변 생성 완료")

        return ChatResponse(
            answer=answer,
            sources=sources,
            engine=selected_engine,
            product_id=request.product_id,
            suggested_questions=suggested
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # 보안: 내부 예외 메시지/스택을 클라이언트에 그대로 노출하지 않습니다.
        logger.exception("챗봇 처리 중 오류")
        raise HTTPException(status_code=500, detail="챗봇 처리 중 오류가 발생했습니다.")
