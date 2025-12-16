"""
SQLite 데이터베이스 연결 및 초기화
- 테이블 생성
- 더미 데이터 시드
"""
import sqlite3
import os
from pathlib import Path
import logging
import json
import csv

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


def init_db():
    """
    데이터베이스 초기화
    1. 테이블 재생성
    2. 더미 데이터 시드 (@dummies 기반)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 0. 기존 테이블 삭제 (스키마 변경 반영)
        cursor.executescript(
            """
            DROP TABLE IF EXISTS order_reviews;
            DROP TABLE IF EXISTS product_qna;
            DROP TABLE IF EXISTS products;
            """
        )
        conn.commit()

        # 1. 테이블 생성
        logger.info("테이블 생성 중...")
        
        # products 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                image_url TEXT,
                price INTEGER NOT NULL,
                category TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # order_reviews 테이블 (주문 리뷰)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                user_name TEXT,
                review_text TEXT NOT NULL,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        # product_qna 테이블 (상품 QnA)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_qna (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        # 인덱스 생성 (검색 성능 향상)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_reviews_product_id 
            ON order_reviews(product_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_qna_product_id 
            ON product_qna(product_id)
        """)
        
        conn.commit()
        logger.info("테이블 생성 완료")
        
        # 2. 더미 데이터 시드
        logger.info("더미 데이터 시드 중... (@dummies 사용)")
        seed_data(conn)
        logger.info("더미 데이터 시드 완료")
            
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def seed_data(conn):
    """@dummies 폴더 기반 더미 데이터 삽입"""
    cursor = conn.cursor()

    products, slug_to_id = _load_dummy_products()
    if not products:
        raise RuntimeError("더미 상품 정보를 찾을 수 없습니다. @dummies/product_info.json을 확인하세요.")

    for product in products:
        cursor.execute(
            """
            INSERT INTO products (id, name, image_url, price, category, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                product["id"],
                product["name"],
                product["image_url"],
                product["price"],
                product["category"],
                product["description"],
            ),
        )

    reviews = _load_dummy_reviews(slug_to_id)
    for review in reviews:
        cursor.execute(
            """
            INSERT INTO order_reviews (product_id, user_name, review_text, rating)
            VALUES (?, ?, ?, ?)
            """,
            (
                review["product_id"],
                review["user_name"],
                review["review_text"],
                review["rating"],
            ),
        )

    qnas = _load_dummy_qnas(slug_to_id)
    for qna in qnas:
        cursor.execute(
            """
            INSERT INTO product_qna (product_id, question, answer)
            VALUES (?, ?, ?)
            """,
            (
                qna["product_id"],
                qna["question"],
                qna["answer"],
            ),
        )

    conn.commit()


# ---------- 더미 데이터 로더 ---------- #

_PRODUCT_ORDER = ["blanket_001", "monitor_001", "noodle_001", "sidiz_t20"]
_PRICE_MAP = {
    "blanket_001": 69000,
    "monitor_001": 399000,
    "noodle_001": 1200,
    "sidiz_t20": 239000,
}


def _dummy_root() -> Path:
    return Path(__file__).resolve().parents[2] / "dummies"


def _compose_description(meta: dict) -> str:
    """구조 필드를 짧은 소개 문장으로 묶습니다."""
    name = meta.get("name", "")
    category = meta.get("category", "")

    parts = []
    if meta.get("features"):
        parts.append(f"주요 특징: {', '.join(meta['features'])}")
    if meta.get("variants"):
        parts.append(f"옵션: {', '.join(meta['variants'])}")
    if meta.get("colors"):
        parts.append(f"색상: {', '.join(meta['colors'])}")
    if meta.get("sizes"):
        parts.append(f"사이즈: {', '.join(meta['sizes'])}")
    if meta.get("materials"):
        parts.append(f"소재: {', '.join(meta['materials'])}")
    if meta.get("delivery_time"):
        parts.append(f"배송: {meta['delivery_time']}")
    if meta.get("shelf_life"):
        parts.append(f"유통기한: {meta['shelf_life']}")
    if meta.get("weight"):
        parts.append(f"중량: {meta['weight']}")

    summary = " ".join(parts)
    if not summary:
        summary = f"{category} 상품입니다."
    return f"{name} - {summary}"


def _load_dummy_products():
    path = _dummy_root() / "product_info.json"
    if not path.exists():
        logger.warning("product_info.json을 찾을 수 없습니다: %s", path)
        return [], {}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    slug_order = [slug for slug in _PRODUCT_ORDER if slug in data] or list(data.keys())
    slug_to_id = {slug: idx for idx, slug in enumerate(slug_order, start=1)}

    products = []
    for slug in slug_order:
        meta = data.get(slug, {})
        products.append(
            {
                "id": slug_to_id[slug],
                "slug": slug,
                "name": meta.get("name", slug),
                "category": meta.get("category", "기타"),
                "description": _compose_description(meta),
                "price": _PRICE_MAP.get(slug, 10000),
                "image_url": f"https://via.placeholder.com/400x400?text={slug}",
            }
        )

    return products, slug_to_id


def _load_dummy_reviews(slug_to_id: dict):
    """@dummies/reviews_* 파일에서 리뷰 로드"""
    reviews = []
    root = _dummy_root()
    user_counter = 1

    for path in sorted(root.glob("reviews_*_all.txt")):
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                slug = row.get("product_id")
                product_id = slug_to_id.get(slug)
                if not product_id:
                    logger.warning("알 수 없는 product_id(%s) - 파일 %s", slug, path.name)
                    continue
                review_text = (row.get("review_text") or "").strip()
                rating_raw = row.get("rating")
                rating = int(rating_raw) if rating_raw else None
                user_name = f"리뷰어 {user_counter}"
                user_counter += 1
                reviews.append(
                    {
                        "product_id": product_id,
                        "user_name": user_name,
                        "review_text": review_text,
                        "rating": rating,
                    }
                )
    return reviews


def _load_dummy_qnas(slug_to_id: dict):
    """@dummies/qna_* 파일에서 QnA 로드"""
    qnas = []
    root = _dummy_root()

    for path in sorted(root.glob("qna_*_all.txt")):
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                slug = row.get("product_id")
                product_id = slug_to_id.get(slug)
                if not product_id:
                    logger.warning("알 수 없는 product_id(%s) - 파일 %s", slug, path.name)
                    continue
                question = (row.get("question") or "").strip()
                answer = (row.get("answer") or "").strip()
                qnas.append(
                    {
                        "product_id": product_id,
                        "question": question,
                        "answer": answer,
                    }
                )
    return qnas
