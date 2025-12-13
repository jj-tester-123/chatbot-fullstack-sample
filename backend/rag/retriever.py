"""
RAG 검색 파이프라인
- DB에서 텍스트 로드
- 청킹
- 임베딩 생성 및 ChromaDB 저장
- 검색
"""
from typing import List, Dict, Any
import logging

from db.repository import get_all_product_texts
from rag.chunker import chunk_product_texts
from rag.vector_store import (
    add_documents,
    search_documents,
    get_collection_stats,
    clear_collection,
)

logger = logging.getLogger(__name__)

# 인덱싱 완료 플래그
_indexed = False


def index_all_products():
    """
    모든 상품 텍스트를 인덱싱
    - DB에서 텍스트 로드
    - 청킹
    - 임베딩 생성 및 ChromaDB 저장
    """
    global _indexed
    
    if _indexed:
        logger.info("이미 인덱싱 완료됨")
        return
    
    logger.info("상품 텍스트 인덱싱 시작...")

    # Chroma는 영구 저장소이므로, 과거 인덱스가 남아있으면 엉뚱한 컨텍스트가 섞여 나올 수 있습니다.
    # 개발/학습용 프로젝트에서는 "DB 내용 = 벡터 인덱스 내용"을 맞추는 것이 중요하므로,
    # 기본적으로 컬렉션을 비우고 재구축합니다.
    # (필요 시 환경변수로 끌 수 있습니다)
    import os
    clear_on_index = os.getenv("RAG_CLEAR_COLLECTION_ON_INDEX", "true").lower() in ["1", "true", "yes", "y", "on"]
    if clear_on_index:
        logger.info("기존 벡터 컬렉션 초기화 후 재인덱싱합니다. (RAG_CLEAR_COLLECTION_ON_INDEX=true)")
        clear_collection()
    
    # 1. DB에서 모든 텍스트 로드
    product_texts = get_all_product_texts()
    logger.info(f"{len(product_texts)}개 텍스트 로드 완료")
    
    if not product_texts:
        logger.warning("인덱싱할 텍스트가 없습니다")
        _indexed = True
        return
    
    # 2. 청킹
    chunked_data = chunk_product_texts(product_texts)
    logger.info(f"{len(chunked_data)}개 청크 생성 완료")
    
    # 3. ChromaDB에 추가
    add_documents(chunked_data)
    
    # 4. 통계 출력
    stats = get_collection_stats()
    logger.info(f"인덱싱 완료: {stats['document_count']}개 문서")
    
    _indexed = True


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
    # 인덱싱이 안 되어 있으면 먼저 인덱싱
    if not _indexed:
        index_all_products()
    
    # 벡터 검색
    results = search_documents(
        query=query,
        product_id=product_id,
        top_k=top_k
    )
    
    return results

