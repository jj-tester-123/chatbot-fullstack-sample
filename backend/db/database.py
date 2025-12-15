"""
SQLite 데이터베이스 연결 및 초기화
- 테이블 생성
- 더미 데이터 시드
"""
import sqlite3
import os
from pathlib import Path
import logging

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
    1. 테이블 생성
    2. 더미 데이터 시드 (테이블이 비어있을 경우)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
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
                order_id INTEGER,
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
        
        # 2. 더미 데이터 시드 (데이터가 없을 경우)
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("더미 데이터 시드 중...")
            seed_data(conn)
            logger.info("더미 데이터 시드 완료")
        else:
            logger.info(f"기존 데이터 존재 ({count}개 상품), 상품 시드 스킵")

            # 기존 DB에 products만 있고 리뷰/QnA가 없는 경우가 있어, 비어 있으면 보조 시드를 수행합니다.
            cursor.execute("SELECT COUNT(*) FROM order_reviews")
            review_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM product_qna")
            qna_count = cursor.fetchone()[0]

            if review_count == 0 and qna_count == 0:
                logger.info("리뷰/Q&A 데이터가 비어 있어 보조 더미 데이터를 시드합니다...")
                seed_reviews_and_qnas(conn)
                logger.info("리뷰/Q&A 보조 시드 완료")
            else:
                logger.info(f"리뷰/Q&A 데이터 존재 (reviews={review_count}, qna={qna_count}), 보조 시드 스킵")
            
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def seed_data(conn):
    """더미 데이터 삽입"""
    cursor = conn.cursor()
    
    # 상품 데이터
    products = [
        {
            "name": "무선 블루투스 이어폰 ProMax",
            "image_url": "https://via.placeholder.com/300x300?text=Earphone",
            "price": 89000,
            "category": "전자기기",
            "description": """무선 블루투스 이어폰 ProMax는 최신 블루투스 5.3 기술을 탑재하여 안정적인 연결과 낮은 지연시간을 제공합니다.
액티브 노이즈 캔슬링(ANC) 기능으로 주변 소음을 최대 35dB까지 차단하여 몰입감 있는 청취 경험을 선사합니다.
IPX7 방수 등급으로 땀과 물에 강하며, 운동 중에도 안심하고 사용할 수 있습니다.
한 번 충전으로 최대 8시간 재생이 가능하며, 충전 케이스 사용 시 총 32시간까지 사용 가능합니다."""
        },
        {
            "name": "스마트워치 FitPro X1",
            "image_url": "https://via.placeholder.com/300x300?text=Smartwatch",
            "price": 159000,
            "category": "웨어러블",
            "description": """스마트워치 FitPro X1은 건강과 피트니스를 위한 올인원 솔루션입니다.
심박수, 혈중 산소 포화도, 수면 패턴, 스트레스 레벨을 24시간 모니터링합니다.
100가지 이상의 운동 모드를 지원하며, GPS 내장으로 야외 활동 시 정확한 거리와 경로를 추적합니다.
1.4인치 AMOLED 디스플레이로 선명한 화면을 제공하며, 항상 켜진 디스플레이(AOD) 기능을 지원합니다.
5ATM 방수로 수영 중에도 착용 가능하며, 배터리는 일반 사용 시 최대 14일까지 지속됩니다."""
        },
        {
            "name": "USB-C 고속 충전 케이블",
            "image_url": "https://via.placeholder.com/300x300?text=Cable",
            "price": 15000,
            "category": "액세서리",
            "description": """USB-C 고속 충전 케이블은 최대 100W(20V/5A)의 전력 전송을 지원하여 노트북, 태블릿, 스마트폰을 빠르게 충전할 수 있습니다.
USB 3.2 Gen 2 규격으로 최대 10Gbps의 데이터 전송 속도를 제공합니다.
이중 나일론 브레이드 소재로 제작되어 내구성이 뛰어나며, 20,000회 이상의 굽힘 테스트를 통과했습니다.
1.8m 길이로 사용 시 여유롭게 사용할 수 있으며, 알루미늄 커넥터로 고급스러운 디자인을 자랑합니다."""
        }
    ]
    
    for product in products:
        cursor.execute("""
            INSERT INTO products (name, image_url, price, category, description)
            VALUES (?, ?, ?, ?, ?)
        """, (
            product["name"],
            product["image_url"],
            product["price"],
            product["category"],
            product["description"]
        ))
    
    conn.commit()
    
    # order_reviews 데이터 (주문 리뷰)
    _seed_reviews(cursor)
    _seed_qnas(cursor)
    conn.commit()


def seed_reviews_and_qnas(conn):
    """
    보조 더미 데이터 삽입
    - products는 유지하고, 리뷰/질문답변만 삽입합니다.
    """
    cursor = conn.cursor()
    _seed_reviews(cursor)
    _seed_qnas(cursor)
    conn.commit()


def _seed_reviews(cursor):
    """order_reviews 더미 데이터 삽입"""
    reviews = [
        # 상품 1: 무선 블루투스 이어폰
        {
            "product_id": 1,
            "order_id": 1001,
            "user_name": "김철수",
            "review_text": "음질이 정말 좋아요! 저음이 풍부하고 고음도 깨끗합니다. 노이즈 캔슬링 기능도 훌륭해서 지하철에서도 음악에 집중할 수 있어요. 배터리도 오래가고 충전도 빨라서 만족스럽습니다. 가격 대비 성능이 뛰어난 제품입니다.",
            "rating": 5
        },
        {
            "product_id": 1,
            "order_id": 1002,
            "user_name": "이영희",
            "review_text": "디자인이 세련되고 착용감이 편안합니다. 장시간 착용해도 귀가 아프지 않아요. 통화 품질도 좋아서 업무용으로도 사용하고 있습니다. 다만 케이스가 조금 큰 편이라 주머니에 넣기엔 부담스러워요.",
            "rating": 4
        },
        {
            "product_id": 1,
            "order_id": 1003,
            "user_name": "박민수",
            "review_text": "방수 기능이 있어서 운동할 때 안심하고 사용할 수 있어요. IPX7 등급이라 땀에 강하고, 비 오는 날에도 걱정 없습니다.",
            "rating": 5
        },
        
        # 상품 2: 스마트워치
        {
            "product_id": 2,
            "order_id": 2001,
            "user_name": "최지영",
            "review_text": "운동할 때 정말 유용해요! 심박수와 칼로리 소모량을 실시간으로 확인할 수 있어서 운동 효율이 높아졌습니다. 수면 분석 기능도 정확해서 수면 패턴을 개선하는 데 도움이 되었어요. 배터리도 오래가서 자주 충전할 필요가 없어 편리합니다.",
            "rating": 5
        },
        {
            "product_id": 2,
            "order_id": 2002,
            "user_name": "정대현",
            "review_text": "디자인이 심플하고 고급스러워요. 화면도 밝고 선명해서 야외에서도 잘 보입니다. 다만 앱 연동이 처음엔 조금 복잡했어요. 익숙해지니 괜찮지만 초기 설정 가이드가 더 자세했으면 좋겠습니다.",
            "rating": 4
        },
        {
            "product_id": 2,
            "order_id": 2003,
            "user_name": "한소연",
            "review_text": "GPS 기능이 정확해서 러닝할 때 경로 추적이 잘 됩니다. 배터리 수명도 기대 이상으로 길어서 만족합니다.",
            "rating": 5
        },
        
        # 상품 3: USB-C 케이블
        {
            "product_id": 3,
            "order_id": 3001,
            "user_name": "강동욱",
            "review_text": "충전 속도가 정말 빠릅니다! 노트북 충전도 문제없이 잘 되고, 케이블이 튼튼해서 오래 쓸 수 있을 것 같아요. 길이도 적당해서 침대에서 사용하기 편합니다. 가격 대비 품질이 훌륭한 제품입니다.",
            "rating": 5
        },
        {
            "product_id": 3,
            "order_id": 3002,
            "user_name": "윤서진",
            "review_text": "디자인이 깔끔하고 마감도 좋습니다. 케이블이 꼬이지 않아서 사용하기 편해요. 다만 조금 무거운 편이라 휴대용으로는 가벼운 케이블이 더 나을 것 같습니다.",
            "rating": 4
        },
        {
            "product_id": 3,
            "order_id": 3003,
            "user_name": "오준호",
            "review_text": "데이터 전송 속도도 빠르고 충전도 잘 됩니다. 내구성도 좋아 보여서 오래 사용할 수 있을 것 같아요.",
            "rating": 5
        }
    ]
    
    for review in reviews:
        cursor.execute("""
            INSERT INTO order_reviews (product_id, order_id, user_name, review_text, rating)
            VALUES (?, ?, ?, ?, ?)
        """, (
            review["product_id"],
            review["order_id"],
            review["user_name"],
            review["review_text"],
            review["rating"]
        ))


def _seed_qnas(cursor):
    """product_qna 더미 데이터 삽입"""
    qnas = [
        # 상품 1: 무선 블루투스 이어폰
        {
            "product_id": 1,
            "question": "아이폰과 안드로이드 모두 호환되나요?",
            "answer": "네, 블루투스 표준 프로토콜을 사용하므로 모든 스마트폰과 호환됩니다."
        },
        {
            "product_id": 1,
            "question": "방수 기능이 있나요?",
            "answer": "IPX7 등급의 방수 기능이 있어 땀과 물에 강합니다. 다만 완전 침수는 피해주세요."
        },
        {
            "product_id": 1,
            "question": "배터리는 얼마나 오래 가나요?",
            "answer": "한 번 충전으로 최대 8시간 재생이 가능하며, 충전 케이스 사용 시 총 32시간까지 사용 가능합니다."
        },
        
        # 상품 2: 스마트워치
        {
            "product_id": 2,
            "question": "아이폰과 안드로이드 모두 사용 가능한가요?",
            "answer": "네, iOS와 Android 모두 지원합니다. 전용 앱을 다운로드하여 연동하시면 됩니다."
        },
        {
            "product_id": 2,
            "question": "수영할 때 착용해도 되나요?",
            "answer": "5ATM 방수 등급으로 수영 중 착용 가능합니다. 다만 다이빙이나 고압 수중 활동은 피해주세요."
        },
        {
            "product_id": 2,
            "question": "배터리는 얼마나 오래 가나요?",
            "answer": "일반 사용 시 최대 14일까지 지속됩니다. GPS 사용 시에는 배터리 소모가 더 빠를 수 있습니다."
        },
        
        # 상품 3: USB-C 케이블
        {
            "product_id": 3,
            "question": "맥북 프로 충전이 가능한가요?",
            "answer": "네, 100W 전력 전송을 지원하므로 맥북 프로를 포함한 모든 USB-C 노트북 충전이 가능합니다."
        },
        {
            "product_id": 3,
            "question": "데이터 전송도 되나요?",
            "answer": "네, USB 3.2 Gen 2 규격으로 최대 10Gbps의 고속 데이터 전송을 지원합니다."
        },
        {
            "product_id": 3,
            "question": "케이블 길이는 얼마나 되나요?",
            "answer": "1.8m 길이로 제공되며, 사용 시 여유롭게 사용할 수 있습니다."
        }
    ]
    
    for qna in qnas:
        cursor.execute("""
            INSERT INTO product_qna (product_id, question, answer)
            VALUES (?, ?, ?)
        """, (
            qna["product_id"],
            qna["question"],
            qna["answer"]
        ))

