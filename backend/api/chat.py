"""
챗봇 API 라우터
- POST /chat: RAG + LLM 기반 질의응답
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List
import logging

from services.chat_service import handle_chat

logger = logging.getLogger(__name__)

router = APIRouter()


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
    source_id: str
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
    payload = await handle_chat(
        query=request.query,
        product_id=request.product_id,
        engine=request.engine,
        conversation_history=request.conversation_history,
    )

    # response_model=ChatResponse가 검증/직렬화를 담당합니다.
    return payload
