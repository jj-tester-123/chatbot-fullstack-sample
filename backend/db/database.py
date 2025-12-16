"""
SQLite 데이터베이스 연결 및 초기화
- 테이블 생성
"""
import sqlite3
import os
from pathlib import Path
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 데이터베이스 경로
def _resolve_db_path() -> str:
    """
    SQLite DB 경로를 결정합니다.
    - 기본값은 backend/data/chatbot.db (실행 cwd에 영향받지 않도록)
    - DATABASE_PATH 환경변수가 상대경로면 backend 루트 기준으로 해석합니다.
    """
    backend_root = Path(__file__).resolve().parents[1]
    default_path = backend_root / "data" / "chatbot.db"
    raw = os.getenv("DATABASE_PATH")
    if not raw:
        return str(default_path)
    p = Path(raw)
    if not p.is_absolute():
        p = backend_root / p
    return str(p.resolve())


DB_PATH = _resolve_db_path()


def get_connection():
    """데이터베이스 연결 반환"""
    # 데이터 디렉토리 생성
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # dict 형태로 결과 반환
    return conn


def _drop_existing_tables(cursor):
    cursor.executescript(
        """
        DROP TABLE IF EXISTS order_reviews;
        DROP TABLE IF EXISTS product_qna;
        DROP TABLE IF EXISTS products;
        """
    )


def _create_tables(cursor):
    # products 테이블
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            image_url TEXT,
            price INTEGER NOT NULL,
            category TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # order_reviews 테이블 (주문 리뷰)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS order_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_name TEXT,
            review_text TEXT NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
    )

    # product_qna 테이블 (상품 QnA)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS product_qna (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
    )

    # 인덱스 생성 (검색 성능 향상)
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_order_reviews_product_id 
        ON order_reviews(product_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_product_qna_product_id 
        ON product_qna(product_id)
        """
    )


def init_db(*, reset: bool = False):
    """
    데이터베이스 초기화
    - reset=True일 경우 테이블을 드롭 후 재생성 (개발용)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if reset:
            logger.info("DB 테이블을 재생성합니다. (reset=True)")
            _drop_existing_tables(cursor)

        _create_tables(cursor)
        conn.commit()
        logger.info("테이블 생성/확인 완료")
            
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()
