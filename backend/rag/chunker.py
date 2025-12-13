"""
텍스트 청킹(분할) 모듈
- 긴 텍스트를 적절한 크기로 분할
- 오버랩을 두어 문맥 유지
"""
from typing import List, Dict, Any
import re


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[str]:
    """
    텍스트를 청크로 분할
    
    Args:
        text: 분할할 텍스트
        chunk_size: 청크 크기 (문자 수)
        chunk_overlap: 청크 간 오버랩 (문자 수)
        
    Returns:
        청크 리스트
    """
    # 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # 마지막 청크가 아니면 문장 경계에서 자르기
        if end < len(text):
            # 마침표, 느낌표, 물음표 등에서 자르기
            last_period = max(
                text.rfind('.', start, end),
                text.rfind('!', start, end),
                text.rfind('?', start, end),
                text.rfind('\n', start, end)
            )
            
            if last_period > start:
                end = last_period + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # 다음 청크 시작 위치 (오버랩 고려)
        start = end - chunk_overlap
        
        # 무한 루프 방지
        if start <= 0 or start >= len(text):
            break
    
    return chunks


def chunk_product_texts(
    product_texts: List[Dict[str, Any]],
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    상품 텍스트 리스트를 청크로 분할
    
    Args:
        product_texts: 상품 텍스트 리스트 (DB에서 조회한 데이터)
        chunk_size: 청크 크기
        chunk_overlap: 청크 간 오버랩
        
    Returns:
        청크 리스트 (메타데이터 포함)
    """
    chunked_data = []
    
    for text_data in product_texts:
        content = text_data["content"]
        chunks = chunk_text(content, chunk_size, chunk_overlap)
        
        for i, chunk in enumerate(chunks):
            chunked_data.append({
                "content": chunk,
                "product_id": text_data["product_id"],
                "type": text_data["type"],
                "original_id": text_data["id"],
                "chunk_index": i
            })
    
    return chunked_data

