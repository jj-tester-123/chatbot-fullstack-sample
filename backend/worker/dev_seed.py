"""
개발용 더미 데이터 시더
- dummies 폴더의 JSON/TSV를 읽어 DB에 삽입
"""

from __future__ import annotations

import csv
import json
import logging
import os
from pathlib import Path
from typing import Optional

from db.database import get_connection

logger = logging.getLogger(__name__)


def should_seed_dummies(seed_flag: Optional[bool] = None) -> bool:
    """
    더미 데이터 시드를 수행할지 결정
    - 인자(seed_flag)가 명시되면 우선 사용
    - 그 외에는 환경변수 DATABASE_SEED_DUMMIES가 true일 때
    """
    if seed_flag is not None:
        return seed_flag
    raw = os.getenv("DATABASE_SEED_DUMMIES")
    return raw is not None and raw.lower() in ["1", "true", "yes", "y", "on"]


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


def _has_existing_products(cursor) -> bool:
    try:
        cursor.execute("SELECT COUNT(1) FROM products")
        row = cursor.fetchone()
        return bool(row and row[0] > 0)
    except Exception:
        return False


def seed_dummies_if_needed(seed_flag: Optional[bool] = None):
    """환경/플래그 기반으로 더미 데이터를 시드 (이미 있으면 스킵)"""
    if not should_seed_dummies(seed_flag):
        logger.info("더미 데이터 시드를 스킵합니다. (DATABASE_SEED_DUMMIES=false 또는 플래그 미설정)")
        return

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if _has_existing_products(cursor):
            logger.info("기존 데이터가 있어 더미 시드를 건너뜁니다.")
            return
        logger.info("더미 데이터 시드 중... (@dummies 사용)")
        seed_data(conn)
        logger.info("더미 데이터 시드 완료")
    finally:
        conn.close()
