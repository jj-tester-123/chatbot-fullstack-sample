"""
데이터베이스 리포지토리 레이어
- 상품 조회
- 상품 텍스트 조회 (여러 테이블 통합)
"""
from typing import List, Optional, Dict, Any
from db.database import get_connection


def get_all_products() -> List[Dict[str, Any]]:
    """모든 상품 목록 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, image_url, price, category, description
        FROM products
        ORDER BY id
    """)
    
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return products


def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """특정 상품 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, image_url, price, category, description
        FROM products
        WHERE id = ?
    """, (product_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_product_texts(product_id: int, text_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    특정 상품의 텍스트 조회 (레거시 호환용 - 빈 리스트 반환)
    
    Args:
        product_id: 상품 ID
        text_type: 텍스트 타입 필터 (사용하지 않음)
    """
    # 레거시 호환을 위해 빈 리스트 반환
    # 실제 데이터는 get_all_product_texts_for_rag() 사용
    return []


def get_all_product_texts() -> List[Dict[str, Any]]:
    """
    모든 상품 텍스트 조회 (RAG 인덱싱용)
    - products.description
    - order_reviews.review_text
    - product_qna.question + answer
    를 통합하여 반환
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    texts = []
    
    # 1. products 테이블의 description
    cursor.execute("""
        SELECT id, id as product_id, 'description' as type, description as content
        FROM products
        WHERE description IS NOT NULL AND description != ''
        ORDER BY id
    """)
    for row in cursor.fetchall():
        texts.append(dict(row))
    
    # 2. order_reviews 테이블의 review_text
    cursor.execute("""
        SELECT id, product_id, 'review' as type, review_text as content
        FROM order_reviews
        WHERE review_text IS NOT NULL AND review_text != ''
        ORDER BY product_id, id
    """)
    for row in cursor.fetchall():
        texts.append(dict(row))
    
    # 3. product_qna 테이블의 question + answer
    cursor.execute("""
        SELECT 
            id, 
            product_id, 
            'qna' as type, 
            'Q: ' || question || '\nA: ' || answer as content
        FROM product_qna
        WHERE question IS NOT NULL AND answer IS NOT NULL
        ORDER BY product_id, id
    """)
    for row in cursor.fetchall():
        texts.append(dict(row))
    
    conn.close()
    
    return texts


def get_product_texts_by_ids(product_ids: List[int]) -> List[Dict[str, Any]]:
    """
    선택된 제품 ID 리스트의 텍스트 조회 (RAG 인덱싱용)
    - products.description
    - order_reviews.review_text
    - product_qna.question + answer
    를 통합하여 반환
    
    Args:
        product_ids: 상품 ID 리스트
        
    Returns:
        텍스트 리스트
    """
    if not product_ids:
        return []
    
    conn = get_connection()
    cursor = conn.cursor()
    
    texts = []
    placeholders = ','.join(['?'] * len(product_ids))
    
    # 1. products 테이블의 description
    cursor.execute(f"""
        SELECT id, id as product_id, 'description' as type, description as content
        FROM products
        WHERE id IN ({placeholders}) 
        AND description IS NOT NULL AND description != ''
        ORDER BY id
    """, product_ids)
    for row in cursor.fetchall():
        texts.append(dict(row))
    
    # 2. order_reviews 테이블의 review_text
    cursor.execute(f"""
        SELECT id, product_id, 'review' as type, review_text as content
        FROM order_reviews
        WHERE product_id IN ({placeholders})
        AND review_text IS NOT NULL AND review_text != ''
        ORDER BY product_id, id
    """, product_ids)
    for row in cursor.fetchall():
        texts.append(dict(row))
    
    # 3. product_qna 테이블의 question + answer
    cursor.execute(f"""
        SELECT 
            id, 
            product_id, 
            'qna' as type, 
            'Q: ' || question || '\nA: ' || answer as content
        FROM product_qna
        WHERE product_id IN ({placeholders})
        AND question IS NOT NULL AND answer IS NOT NULL
        ORDER BY product_id, id
    """, product_ids)
    for row in cursor.fetchall():
        texts.append(dict(row))
    
    conn.close()
    
    return texts

