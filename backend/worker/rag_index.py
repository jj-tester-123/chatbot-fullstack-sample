"""
RAG 인덱싱 워커

사용 예:
  cd backend
  ./venv/bin/python -m worker.rag_index --clear

옵션:
  --product-ids 1,2,3   특정 상품만 인덱싱
  --clear / --no-clear  컬렉션 초기화 여부

보안:
- 이 워커는 LLM API 키가 필요하지 않습니다(임베딩은 로컬 모델 사용).
- 다만 환경변수(.env)에 포함된 키가 로그로 노출되지 않도록 주의하세요.
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import List, Optional

from dotenv import load_dotenv

from db.database import init_db
from rag.indexer import index_products


def _parse_product_ids(raw: Optional[str]) -> Optional[List[int]]:
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return None
    return [int(p) for p in parts]


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 외부 라이브러리 로그가 과도할 수 있어 최소화합니다.
    logging.getLogger("chromadb.segment.impl.vector.local_persistent_hnsw").setLevel(logging.ERROR)
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.ERROR)
    logging.getLogger("chromadb").setLevel(logging.ERROR)
    logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

    # 로컬 개발 편의를 위해 .env를 자동 로드합니다.
    load_dotenv()

    parser = argparse.ArgumentParser(description="RAG 인덱싱 워커 (ChromaDB 재구축/업데이트)")
    parser.add_argument(
        "--product-ids",
        default=None,
        help="특정 상품만 인덱싱할 ID 리스트 (예: 1,2,3). 미지정 시 전체 인덱싱",
    )
    parser.add_argument(
        "--clear",
        dest="clear",
        action="store_true",
        help="인덱싱 전 컬렉션을 비우고 재구축합니다.",
    )
    parser.add_argument(
        "--no-clear",
        dest="clear",
        action="store_false",
        help="기존 컬렉션을 유지한 채 upsert합니다.",
    )
    parser.set_defaults(clear=None)

    args = parser.parse_args()

    # 워커는 DB 스키마가 없으면 실패하므로 초기화 보장 (seed 포함)
    logger.info("DB 초기화 확인 중...")
    init_db()

    product_ids = _parse_product_ids(args.product_ids)
    clear_on_index = args.clear
    if clear_on_index is None:
        clear_on_index = os.getenv("RAG_CLEAR_COLLECTION_ON_INDEX", "true").lower() in [
            "1",
            "true",
            "yes",
            "y",
            "on",
        ]

    logger.info("RAG 인덱싱 시작 (product_ids=%s, clear_on_index=%s)", product_ids, clear_on_index)
    stats = index_products(product_ids=product_ids, clear_on_index=clear_on_index)
    logger.info("RAG 인덱싱 종료: %s", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


