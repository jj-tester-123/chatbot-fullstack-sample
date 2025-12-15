"""
ChromaDB 벡터 스토어 관리
- 컬렉션 생성 및 관리
- 문서 추가/검색
- product_id 필터링
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import logging

from rag.embedder import get_embeddings, get_embedding

logger = logging.getLogger(__name__)

# ChromaDB 클라이언트 (전역)
_chroma_client = None
_collection = None

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
COLLECTION_NAME = "product_texts"


def init_chroma():
    """ChromaDB 초기화"""
    global _chroma_client, _collection
    
    if _chroma_client is None:
        logger.info("ChromaDB 초기화 중...")
        
        # 영구 저장소 설정
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # 컬렉션 가져오기 또는 생성
        try:
            _collection = _chroma_client.get_collection(name=COLLECTION_NAME)
            logger.info(f"기존 컬렉션 로드: {COLLECTION_NAME}")
        except:
            _collection = _chroma_client.create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "상품 텍스트 임베딩"}
            )
            logger.info(f"새 컬렉션 생성: {COLLECTION_NAME}")
    
    return _collection


def get_collection():
    """컬렉션 반환 (초기화되지 않았으면 초기화)"""
    if _collection is None:
        init_chroma()
    return _collection


def add_documents(documents: List[Dict[str, Any]]):
    """
    문서를 벡터 스토어에 추가
    
    Args:
        documents: 문서 리스트
            - content: 텍스트 내용
            - product_id: 상품 ID
            - type: 텍스트 타입
            - original_id: 원본 DB ID
            - chunk_index: 청크 인덱스
    """
    collection = get_collection()
    
    if not documents:
        logger.warning("추가할 문서가 없습니다")
        return
    
    total = len(documents)
    logger.info(f"임베딩 생성 중... (count={total})")
    
    # 임베딩 생성
    contents = [doc["content"] for doc in documents]
    embeddings = get_embeddings(contents)
    
    # ChromaDB에 추가
    # IMPORTANT: original_id는 각 테이블(products/order_reviews/product_qna)에서 1부터 다시 시작하므로,
    # type을 포함하지 않으면 서로 다른 문서가 같은 ID를 가져 DuplicateIDError가 발생할 수 있습니다.
    ids = [
        f"{doc['product_id']}_{doc['type']}_{doc['original_id']}_{doc['chunk_index']}"
        for doc in documents
    ]
    metadatas = [
        {
            "product_id": str(doc["product_id"]),
            "type": doc["type"],
            "original_id": str(doc["original_id"]),
            "chunk_index": str(doc["chunk_index"])
        }
        for doc in documents
    ]
    
    if hasattr(collection, "upsert"):
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas,
        )
        logger.info(f"벡터 인덱스 반영 완료 (upsert count={total})")
    else:
        # 구버전 호환: upsert가 없다면 add를 쓰되, 중복으로 인한 경고가 길어질 수 있음
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas,
        )
        logger.info(f"벡터 인덱스 반영 완료 (add count={total})")


def search_documents(
    query: str,
    product_id: int,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    벡터 검색 (product_id로 필터링)
    
    Args:
        query: 검색 쿼리
        product_id: 상품 ID (필터)
        top_k: 반환할 문서 수
        
    Returns:
        검색 결과 리스트
    """
    collection = get_collection()
    
    # 쿼리 임베딩 생성
    query_embedding = get_embedding(query)
    
    # ChromaDB 검색 (product_id 필터 적용)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"product_id": str(product_id)}  # 필터: 해당 상품만
    )
    
    # 결과 파싱
    documents = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            documents.append({
                "content": results["documents"][0][i],
                "type": results["metadatas"][0][i]["type"],
                # Chroma distance는 메트릭/데이터에 따라 1보다 커질 수 있으므로,
                # (1 - distance) 같은 단순 변환은 음수 유사도를 만들어 가드 로직을 망가뜨립니다.
                # 안전한 정규화: similarity = 1 / (1 + distance) ∈ (0, 1]
                "score": 1.0 / (1.0 + float(distance)),
                "product_id": int(results["metadatas"][0][i]["product_id"])
            })
    
    return documents


def clear_collection():
    """컬렉션 초기화 (모든 문서 삭제)"""
    global _collection
    
    if _chroma_client:
        try:
            _chroma_client.delete_collection(name=COLLECTION_NAME)
            logger.info(f"컬렉션 삭제: {COLLECTION_NAME}")
        except:
            pass
        
        _collection = _chroma_client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "상품 텍스트 임베딩"}
        )
        logger.info(f"컬렉션 재생성: {COLLECTION_NAME}")


def get_collection_stats():
    """컬렉션 통계 반환"""
    collection = get_collection()
    count = collection.count()
    return {"document_count": count}

