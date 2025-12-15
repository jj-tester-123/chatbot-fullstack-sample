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
    특정 상품의 텍스트 조회 (설명/리뷰/Q&A 통합)
    
    Args:
        product_id: 상품 ID
        text_type: 텍스트 타입 필터 (description/review/qna)
    """
    texts: List[Dict[str, Any]] = []

    # 1) description은 products.description에서 가져옵니다.
    product = get_product_by_id(product_id)
    if product and product.get("description"):
        texts.append(
            {
                "id": product["id"],
                "product_id": product["id"],
                "type": "description",
                "content": product["description"],
            }
        )

    # 2) 리뷰
    for r in get_product_reviews(product_id):
        texts.append(
            {
                "id": r["id"],
                "product_id": r["product_id"],
                "type": "review",
                "content": r["review_text"],
            }
        )

    # 3) QnA
    for q in get_product_qnas(product_id):
        texts.append(
            {
                "id": q["id"],
                "product_id": q["product_id"],
                "type": "qna",
                "content": f"Q: {q['question']}\nA: {q['answer']}",
            }
        )

    if text_type:
        texts = [t for t in texts if t.get("type") == text_type]

    # 최신순: id 내림차순(각 테이블별 autoincrement) 기준
    texts.sort(key=lambda t: t.get("id", 0), reverse=True)
    return texts


def get_product_reviews(product_id: int) -> List[Dict[str, Any]]:
    """특정 상품의 리뷰 조회 (최신순)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, product_id, order_id, user_name, review_text, rating, created_at
        FROM order_reviews
        WHERE product_id = ?
        ORDER BY datetime(created_at) DESC, id DESC
        """,
        (product_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_product_qnas(product_id: int) -> List[Dict[str, Any]]:
    """특정 상품의 Q&A 조회 (최신순)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, product_id, question, answer, created_at
        FROM product_qna
        WHERE product_id = ?
        ORDER BY datetime(created_at) DESC, id DESC
        """,
        (product_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


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

