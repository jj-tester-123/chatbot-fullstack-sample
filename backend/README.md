# RAG 챗봇 백엔드 (FastAPI)

상품 데이터 기반 RAG(Retrieval-Augmented Generation) 검색과 LLM을 사용한 챗봇 백엔드 API입니다.

## 주요 기능

- **상품 관리 API**: 상품 목록 및 상세 정보 조회
- **RAG 기반 챗봇**: ChromaDB를 사용한 벡터 검색 + LLM 응답 생성
- **product_id 범위 제한**: 특정 상품에 대한 질문만 해당 상품 데이터에서 검색

## 프로젝트 구조

```
backend/
├── main.py                 # FastAPI 앱 엔트리포인트
├── api/                    # API 라우터
│   ├── products.py        # 상품 관련 API
│   └── chat.py            # 챗봇 API
├── db/                     # 데이터베이스
│   ├── database.py        # SQLite 연결 및 초기화
│   └── repository.py      # 데이터 조회 레이어
├── rag/                    # RAG 파이프라인
│   ├── embedder.py        # 임베딩 생성
│   ├── chunker.py         # 텍스트 청킹
│   ├── vector_store.py    # ChromaDB 관리
│   └── retriever.py       # 검색 파이프라인
├── llm/                    # LLM 엔진
│   ├── prompt.py          # 공통 프롬프트
│   ├── gemini_engine.py   # Gemini API
│   └── engine.py          # 엔진 통합 인터페이스
├── requirements.txt        # Python 의존성
├── env.example            # 환경 변수 예시
└── README.md              # 이 파일
```

## 설치 및 실행

### 1. Python 가상환경 생성 및 활성화

**방법 A: venv 사용 (권장)**
```bash
cd backend
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**방법 B: conda 사용 (선택사항)**
```bash
cd backend
conda create -n chatbot-backend python=3.10 -y
conda activate chatbot-backend
```

> **참고**: conda 사용자를 위한 상세 가이드는 [INSTALL_CONDA.md](INSTALL_CONDA.md)를 참고하세요.

### 2. 의존성 설치

```bash
# 중요: pip/uvicorn을 PATH에서 찾지 말고, "venv 파이썬"으로 명시 실행하세요.
# (mise/conda/miniforge 등 다른 Python이 섞이면 설치/실행 환경이 달라져 오류가 납니다)
./venv/bin/python -m pip install -r requirements.txt

# Windows
venv\Scripts\python -m pip install -r requirements.txt
```

**주의사항**:
- **가상환경 활성화 확인**: `pip install` 전에 venv 또는 conda 환경이 활성화되어 있는지 확인하세요
- **PyTorch 설치**: 시스템에 맞는 버전을 선택하세요
- CUDA: https://pytorch.org/get-started/locally/
- MPS (Apple Silicon): 기본 설치로 자동 지원
- CPU: 기본 설치

### 3. 환경 변수 설정

`env.example`을 복사하여 `.env` 파일을 생성하고 API 키를 설정합니다.

```bash
cp env.example .env
```

`.env` 파일 편집:

```env
# Gemini API 키 (필수: Gemini 엔진 사용 시)
GEMINI_API_KEY=your_actual_gemini_api_key_here

# Gemini 모델명 (선택)
# 예: gemini-2.5-flash-lite, gemini-2.5-flash ...
GEMINI_MODEL=gemini-2.5-flash-lite

# Hugging Face 토큰 (선택사항, 공개 모델은 토큰 없이도 다운로드 가능)
HF_TOKEN=your_huggingface_token_here

# 데이터베이스 및 ChromaDB 경로
DATABASE_PATH=./data/chatbot.db
CHROMA_PERSIST_DIR=./data/chroma
```

**보안 주의사항**:
- `.env` 파일은 절대 Git에 커밋하지 마세요 (`.gitignore`에 포함됨)
- API 키는 소스 코드에 하드코딩하지 마세요
- Gemini API 키는 [Google AI Studio](https://makersuite.google.com/app/apikey)에서 발급받을 수 있습니다

### 4. 서버 실행

```bash
# 개발 모드 (자동 리로드)
./venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Windows
venv\Scripts\python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 모드
./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Windows
venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

서버가 시작되면:
- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health

### 5. 첫 실행 시 주의사항

**데이터베이스 초기화**:
- 첫 실행 시 SQLite 데이터베이스와 더미 데이터가 자동으로 생성됩니다
- `./data/chatbot.db` 파일이 생성됩니다

**ChromaDB 인덱싱**:
- 첫 실행 시 상품 텍스트를 임베딩하여 ChromaDB에 저장합니다
- 이후 실행 시에는 저장된 인덱스를 재사용합니다

## API 엔드포인트

### 상품 관련

#### `GET /products`
모든 상품 목록 조회

**응답 예시**:
```json
[
  {
    "id": 1,
    "name": "무선 블루투스 이어폰 ProMax",
    "image_url": "https://...",
    "price": 89000,
    "category": "전자기기",
    "description": "고음질 무선 블루투스 이어폰..."
  }
]
```

#### `GET /products/{id}`
특정 상품 상세 정보 조회

**응답 예시**:
```json
{
  "product": {
    "id": 1,
    "name": "무선 블루투스 이어폰 ProMax",
    ...
  },
  "texts": [
    {
      "id": 1,
      "product_id": 1,
      "type": "description",
      "content": "상세 설명..."
    }
  ]
}
```

### 챗봇

#### `POST /chat`
RAG + LLM 기반 질의응답

**요청 예시**:
```json
{
  "query": "이 제품의 배터리는 얼마나 가나요?",
  "product_id": 1,
  "engine": "gemini"
}
```

**응답 예시**:
```json
{
  "answer": "무선 블루투스 이어폰 ProMax는 한 번 충전으로 최대 8시간 재생이 가능하며...",
  "sources": [
    {
      "content": "한 번 충전으로 최대 8시간 재생이 가능하며...",
      "type": "description",
      "score": 0.92
    }
  ],
  "engine": "gemini",
  "product_id": 1
}
```

**파라미터**:
- `query`: 사용자 질문 (필수)
- `product_id`: 상품 ID (필수, 검색 범위 제한)
- `engine`: LLM 엔진 선택 (필수)
  - `"gemini"`: Gemini API 사용

## 트러블슈팅

### 1. Gemini API 오류
```
Gemini API가 초기화되지 않았습니다.
```
**해결 방법**:
- `.env` 파일에 `GEMINI_API_KEY` 설정 확인
- API 키 유효성 확인

### 2. ChromaDB 오류
```
ChromaDB 초기화 실패
```
**해결 방법**:
- `./data/chroma` 디렉토리 삭제 후 재시작
- 디스크 공간 확인

### RAG 검색 성능 향상
1. **청크 크기 조정**: `rag/chunker.py`의 `chunk_size` 파라미터
2. **top_k 조정**: 검색할 컨텍스트 수 조정
3. **임베딩 모델 교체**: 더 빠른 모델로 교체 가능

## 테스트

```bash
# API 테스트 (서버 실행 후)
curl http://localhost:8000/health

# 상품 목록 조회
curl http://localhost:8000/products

# 챗봇 테스트
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "배터리는 얼마나 가나요?", "product_id": 1, "engine": "gemini"}'
```

## 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.

## 기여

이슈 및 풀 리퀘스트를 환영합니다!

