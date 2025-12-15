"""
RAG 인덱서 (배치/워커용)
- DB에서 텍스트 로드
- 청킹
- 임베딩 생성 및 ChromaDB 저장

주의:
- API 서버 프로세스에서는 인덱싱을 자동 수행하지 않는 것을 권장합니다.
  (인덱싱은 별도 워커/배치로 수행하고, API는 조회만 담당)
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import logging
import os

from db.repository import get_all_product_texts, get_product_texts_by_ids
from rag.chunker import chunk_product_texts
from rag.vector_store import add_documents, get_collection_stats, clear_collection

logger = logging.getLogger(__name__)


def index_products(
    *,
    product_ids: Optional[List[int]] = None,
    clear_on_index: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    상품 텍스트를 ChromaDB에 인덱싱합니다.

    Args:
        product_ids: 특정 상품만 인덱싱할 경우 ID 리스트 (None이면 전체)
        clear_on_index: True면 컬렉션을 비우고 재구축 (None이면 env 기반)

    Returns:
        {"indexed_chunks": int, "document_count": int}
    """
    if clear_on_index is None:
        clear_on_index = os.getenv("RAG_CLEAR_COLLECTION_ON_INDEX", "true").lower() in [
            "1",
            "true",
            "yes",
            "y",
            "on",
        ]

    if clear_on_index:
        logger.info(
            "기존 벡터 컬렉션 초기화 후 재인덱싱합니다. (RAG_CLEAR_COLLECTION_ON_INDEX=true)"
        )
        clear_collection()

    # 1) DB에서 텍스트 로드
    if product_ids:
        product_texts = get_product_texts_by_ids(product_ids)
        logger.info("선택 상품 텍스트 로드 완료 (products=%s, texts=%s)", len(product_ids), len(product_texts))
    else:
        product_texts = get_all_product_texts()
        logger.info("전체 상품 텍스트 로드 완료 (texts=%s)", len(product_texts))

    if not product_texts:
        logger.warning("인덱싱할 텍스트가 없습니다.")
        stats = get_collection_stats()
        return {"indexed_chunks": 0, "document_count": stats["document_count"]}

    # 2) 청킹
    chunked_data = chunk_product_texts(product_texts)
    logger.info("청크 생성 완료 (chunks=%s)", len(chunked_data))

    # 3) 벡터 스토어 반영
    add_documents(chunked_data)

    stats = get_collection_stats()
    logger.info("인덱싱 완료 (document_count=%s)", stats["document_count"])
    return {"indexed_chunks": len(chunked_data), "document_count": stats["document_count"]}


