"""
RAG 검색 파이프라인
- DB에서 텍스트 로드
- 청킹
- 임베딩 생성 및 ChromaDB 저장
- 검색
"""
from typing import List, Dict, Any
import logging

from rag.vector_store import (
    search_documents,
    get_collection_stats,
)

logger = logging.getLogger(__name__)

def retrieve_context(
    query: str,
    product_id: int,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    RAG 검색: 질문과 관련된 컨텍스트 검색
    
    Args:
        query: 검색 쿼리
        product_id: 상품 ID (검색 범위 제한)
        top_k: 반환할 컨텍스트 수
        
    Returns:
        검색된 컨텍스트 리스트
    """
    # API 서버는 조회만 수행합니다.
    # 인덱싱(임베딩 생성/업서트)은 별도 워커에서 수행해야 합니다.
    stats = get_collection_stats()
    if int(stats.get("document_count", 0) or 0) <= 0:
        logger.warning(
            "벡터 인덱스가 비어 있습니다. 워커로 인덱싱을 먼저 수행하세요. (document_count=0)"
        )
        return []

    # 벡터 검색
    results = search_documents(
        query=query,
        product_id=product_id,
        top_k=top_k
    )
    
    return results

