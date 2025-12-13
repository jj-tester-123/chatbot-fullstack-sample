"""
데이터베이스 리포지토리 레이어
- 상품 조회
- 상품 텍스트 조회
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
    특정 상품의 텍스트 조회
    
    Args:
        product_id: 상품 ID
        text_type: 텍스트 타입 필터 (None이면 전체)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if text_type:
        cursor.execute("""
            SELECT id, product_id, type, content
            FROM product_texts
            WHERE product_id = ? AND type = ?
            ORDER BY id
        """, (product_id, text_type))
    else:
        cursor.execute("""
            SELECT id, product_id, type, content
            FROM product_texts
            WHERE product_id = ?
            ORDER BY id
        """, (product_id,))
    
    texts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return texts


def get_all_product_texts() -> List[Dict[str, Any]]:
    """모든 상품 텍스트 조회 (RAG 인덱싱용)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, product_id, type, content
        FROM product_texts
        ORDER BY product_id, id
    """)
    
    texts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return texts

