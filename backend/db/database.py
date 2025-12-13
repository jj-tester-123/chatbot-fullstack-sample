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
DB_PATH = os.getenv("DATABASE_PATH", "./data/chatbot.db")


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
        
        # product_texts 테이블 (상품 관련 텍스트: 설명/리뷰/Q&A)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_texts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                type TEXT NOT NULL,  -- description, review, qna
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        # 인덱스 생성 (검색 성능 향상)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_texts_product_id 
            ON product_texts(product_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_texts_type 
            ON product_texts(type)
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
            logger.info(f"기존 데이터 존재 ({count}개 상품), 시드 스킵")
            
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
            "description": "고음질 무선 블루투스 이어폰으로 노이즈 캔슬링 기능이 탑재되어 있습니다."
        },
        {
            "name": "스마트워치 FitPro X1",
            "image_url": "https://via.placeholder.com/300x300?text=Smartwatch",
            "price": 159000,
            "category": "웨어러블",
            "description": "건강 관리와 운동 트래킹이 가능한 스마트워치입니다."
        },
        {
            "name": "USB-C 고속 충전 케이블",
            "image_url": "https://via.placeholder.com/300x300?text=Cable",
            "price": 15000,
            "category": "액세서리",
            "description": "100W 고속 충전을 지원하는 내구성 강한 USB-C 케이블입니다."
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
    
    # product_texts 데이터 (상품별 상세 텍스트)
    product_texts = [
        # 상품 1: 무선 블루투스 이어폰
        {
            "product_id": 1,
            "type": "description",
            "content": """
무선 블루투스 이어폰 ProMax는 최신 블루투스 5.3 기술을 탑재하여 안정적인 연결과 낮은 지연시간을 제공합니다.
액티브 노이즈 캔슬링(ANC) 기능으로 주변 소음을 최대 35dB까지 차단하여 몰입감 있는 청취 경험을 선사합니다.
IPX7 방수 등급으로 땀과 물에 강하며, 운동 중에도 안심하고 사용할 수 있습니다.
한 번 충전으로 최대 8시간 재생이 가능하며, 충전 케이스 사용 시 총 32시간까지 사용 가능합니다.
            """
        },
        {
            "product_id": 1,
            "type": "review",
            "content": "음질이 정말 좋아요! 저음이 풍부하고 고음도 깨끗합니다. 노이즈 캔슬링 기능도 훌륭해서 지하철에서도 음악에 집중할 수 있어요. 배터리도 오래가고 충전도 빨라서 만족스럽습니다. 가격 대비 성능이 뛰어난 제품입니다."
        },
        {
            "product_id": 1,
            "type": "review",
            "content": "디자인이 세련되고 착용감이 편안합니다. 장시간 착용해도 귀가 아프지 않아요. 통화 품질도 좋아서 업무용으로도 사용하고 있습니다. 다만 케이스가 조금 큰 편이라 주머니에 넣기엔 부담스러워요."
        },
        {
            "product_id": 1,
            "type": "qna",
            "content": "Q: 아이폰과 안드로이드 모두 호환되나요?\nA: 네, 블루투스 표준 프로토콜을 사용하므로 모든 스마트폰과 호환됩니다."
        },
        {
            "product_id": 1,
            "type": "qna",
            "content": "Q: 방수 기능이 있나요?\nA: IPX7 등급의 방수 기능이 있어 땀과 물에 강합니다. 다만 완전 침수는 피해주세요."
        },
        
        # 상품 2: 스마트워치
        {
            "product_id": 2,
            "type": "description",
            "content": """
스마트워치 FitPro X1은 건강과 피트니스를 위한 올인원 솔루션입니다.
심박수, 혈중 산소 포화도, 수면 패턴, 스트레스 레벨을 24시간 모니터링합니다.
100가지 이상의 운동 모드를 지원하며, GPS 내장으로 야외 활동 시 정확한 거리와 경로를 추적합니다.
1.4인치 AMOLED 디스플레이로 선명한 화면을 제공하며, 항상 켜진 디스플레이(AOD) 기능을 지원합니다.
5ATM 방수로 수영 중에도 착용 가능하며, 배터리는 일반 사용 시 최대 14일까지 지속됩니다.
            """
        },
        {
            "product_id": 2,
            "type": "review",
            "content": "운동할 때 정말 유용해요! 심박수와 칼로리 소모량을 실시간으로 확인할 수 있어서 운동 효율이 높아졌습니다. 수면 분석 기능도 정확해서 수면 패턴을 개선하는 데 도움이 되었어요. 배터리도 오래가서 자주 충전할 필요가 없어 편리합니다."
        },
        {
            "product_id": 2,
            "type": "review",
            "content": "디자인이 심플하고 고급스러워요. 화면도 밝고 선명해서 야외에서도 잘 보입니다. 다만 앱 연동이 처음엔 조금 복잡했어요. 익숙해지니 괜찮지만 초기 설정 가이드가 더 자세했으면 좋겠습니다."
        },
        {
            "product_id": 2,
            "type": "qna",
            "content": "Q: 아이폰과 안드로이드 모두 사용 가능한가요?\nA: 네, iOS와 Android 모두 지원합니다. 전용 앱을 다운로드하여 연동하시면 됩니다."
        },
        {
            "product_id": 2,
            "type": "qna",
            "content": "Q: 수영할 때 착용해도 되나요?\nA: 5ATM 방수 등급으로 수영 중 착용 가능합니다. 다만 다이빙이나 고압 수중 활동은 피해주세요."
        },
        
        # 상품 3: USB-C 케이블
        {
            "product_id": 3,
            "type": "description",
            "content": """
USB-C 고속 충전 케이블은 최대 100W(20V/5A)의 전력 전송을 지원하여 노트북, 태블릿, 스마트폰을 빠르게 충전할 수 있습니다.
USB 3.2 Gen 2 규격으로 최대 10Gbps의 데이터 전송 속도를 제공합니다.
이중 나일론 브레이드 소재로 제작되어 내구성이 뛰어나며, 20,000회 이상의 굽힘 테스트를 통과했습니다.
1.8m 길이로 사용 시 여유롭게 사용할 수 있으며, 알루미늄 커넥터로 고급스러운 디자인을 자랑합니다.
            """
        },
        {
            "product_id": 3,
            "type": "review",
            "content": "충전 속도가 정말 빠릅니다! 노트북 충전도 문제없이 잘 되고, 케이블이 튼튼해서 오래 쓸 수 있을 것 같아요. 길이도 적당해서 침대에서 사용하기 편합니다. 가격 대비 품질이 훌륭한 제품입니다."
        },
        {
            "product_id": 3,
            "type": "review",
            "content": "디자인이 깔끔하고 마감도 좋습니다. 케이블이 꼬이지 않아서 사용하기 편해요. 다만 조금 무거운 편이라 휴대용으로는 가벼운 케이블이 더 나을 것 같습니다."
        },
        {
            "product_id": 3,
            "type": "qna",
            "content": "Q: 맥북 프로 충전이 가능한가요?\nA: 네, 100W 전력 전송을 지원하므로 맥북 프로를 포함한 모든 USB-C 노트북 충전이 가능합니다."
        },
        {
            "product_id": 3,
            "type": "qna",
            "content": "Q: 데이터 전송도 되나요?\nA: 네, USB 3.2 Gen 2 규격으로 최대 10Gbps의 고속 데이터 전송을 지원합니다."
        }
    ]
    
    for text in product_texts:
        cursor.execute("""
            INSERT INTO product_texts (product_id, type, content)
            VALUES (?, ?, ?)
        """, (
            text["product_id"],
            text["type"],
            text["content"]
        ))
    
    conn.commit()

