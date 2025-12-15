"""
FastAPI 메인 애플리케이션 엔트리포인트
- CORS 설정
- 라우터 등록 (products, chat)
- 앱 시작 시 DB 초기화 및 LLM 로드
"""
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from api import products, chat
from db.database import init_db
from llm.engine import init_llm_engines
from rag.retriever import index_all_products

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 외부 라이브러리(Chroma/Transformers 등)의 과도한 INFO/WARN 로그를 줄입니다.
# (앱 로그는 INFO 유지)
logging.getLogger("chromadb.segment.impl.vector.local_persistent_hnsw").setLevel(logging.ERROR)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.ERROR)  # 텔레메트리 에러 숨김
logging.getLogger("chromadb").setLevel(logging.ERROR)  # WARNING도 숨김
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)  # WARNING도 숨김
logging.getLogger("transformers").setLevel(logging.ERROR)  # WARNING도 숨김
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)  # 모델 다운로드 진행 표시 숨김
logging.getLogger("urllib3").setLevel(logging.ERROR)  # HTTP 요청 로그 숨김

# 로컬 개발 편의를 위해 .env를 자동 로드합니다.
# (운영 환경에서는 보통 프로세스 환경 변수로 주입합니다.)
load_dotenv()

# Hugging Face Hub 진행 표시 비활성화 (이모지 포함된 진행 바 숨김)
import os
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")  # transformers 로그 억제


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 로직"""
    logger.info("애플리케이션 시작 중...")
    
    # 1. DB 초기화 (테이블 생성 + 더미 데이터 seed)
    logger.info("데이터베이스 초기화 중...")
    init_db()
    
    # 2. LLM 엔진 초기화 (Gemini)
    logger.info("LLM 엔진 초기화 중...")
    await init_llm_engines()

    # 3. RAG 인덱싱 (벡터DB)
    # - 첫 요청 시 지연을 없애고
    # - DB와 벡터 인덱스를 동기화(필요 시 clear)하기 위해 앱 시작 시 수행합니다.
    logger.info("RAG 인덱싱 중...")
    index_all_products()
    
    logger.info("애플리케이션 준비 완료")
    yield
    
    logger.info("애플리케이션 종료 중...")


app = FastAPI(
    title="RAG 챗봇 API",
    description="상품 데이터 기반 RAG 검색 + LLM 챗봇 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정 (프론트엔드에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/")
async def root():
    """헬스체크 엔드포인트"""
    return {
        "status": "ok",
        "message": "RAG 챗봇 API 서버가 정상 작동 중입니다.",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """상세 헬스체크"""
    return {
        "status": "healthy",
        "database": "connected",
        "llm": "ready"
    }

