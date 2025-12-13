"""
임베딩 생성 모듈
- sentence-transformers를 사용한 로컬 임베딩
- 추후 Jina/Gemini embeddings로 교체 가능하도록 인터페이스 분리
"""
from typing import List
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# 전역 임베딩 모델 (앱 시작 시 한 번만 로드)
_embedding_model = None


def init_embedder():
    """임베딩 모델 초기화"""
    global _embedding_model
    
    if _embedding_model is None:
        logger.info("임베딩 모델 로드 중...")
        # 한국어 지원이 좋은 multilingual 모델 사용
        model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        _embedding_model = SentenceTransformer(model_name)
        logger.info(f"임베딩 모델 로드 완료: {model_name}")
    
    return _embedding_model


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    텍스트 리스트를 임베딩 벡터로 변환
    
    Args:
        texts: 임베딩할 텍스트 리스트
        
    Returns:
        임베딩 벡터 리스트
    """
    model = init_embedder()
    
    # 배치 처리로 효율적으로 임베딩 생성
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True
    )
    
    return embeddings.tolist()


def get_embedding(text: str) -> List[float]:
    """
    단일 텍스트를 임베딩 벡터로 변환
    
    Args:
        text: 임베딩할 텍스트
        
    Returns:
        임베딩 벡터
    """
    return get_embeddings([text])[0]

