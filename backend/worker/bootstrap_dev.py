"""
개발 환경 부트스트랩 스크립트
- DB 스키마 초기화 (+선택적 reset)
- 더미 데이터 시드
- RAG 인덱싱 (선택)

사용 예:
  cd backend
  ./venv/bin/python -m worker.bootstrap_dev --clear
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import List, Optional

from dotenv import load_dotenv

from db.database import init_db
from worker.dev_seed import seed_dummies_if_needed
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

    load_dotenv()

    parser = argparse.ArgumentParser(
        description="개발용: DB 초기화/더미 시드 + (선택) RAG 인덱싱을 한 번에 수행합니다."
    )
    parser.add_argument(
        "--no-reset-db",
        dest="reset_db",
        action="store_false",
        help="DB 테이블 드롭을 건너뜁니다 (기존 데이터 유지). 기본: reset 후 재생성.",
    )
    parser.add_argument(
        "--no-seed-dummies",
        dest="seed_dummies",
        action="store_false",
        help="더미 데이터 시드를 건너뜁니다. 기본: 더미 데이터 시드.",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="DB 초기화/시드만 수행하고 RAG 인덱싱은 건너뜁니다.",
    )
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
    parser.set_defaults(reset_db=True, seed_dummies=True, clear=None)

    args = parser.parse_args()

    logger.info("DB 초기화 (reset_db=%s)", args.reset_db)
    init_db(reset=args.reset_db)
    seed_dummies_if_needed(args.seed_dummies)

    if args.skip_index:
        logger.info("RAG 인덱싱을 건너뜁니다 (--skip-index).")
        return 0

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
    logger.info("RAG 인덱싱 완료: %s", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
