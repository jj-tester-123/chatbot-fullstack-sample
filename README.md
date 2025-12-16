# RAG 챗봇 풀스택 애플리케이션

상품 데이터(설명, 리뷰, Q&A)를 기반으로 RAG(Retrieval-Augmented Generation) 검색과 LLM을 사용하여 답변하는 챗봇 웹 애플리케이션입니다.

## 프로젝트 개요

- **백엔드**: FastAPI + SQLite + ChromaDB
- **프론트엔드**: Vite + React + TypeScript
- **LLM 엔진**: Gemini API
- **배포**: 로컬 실행 전용 (배포 고려 안 함)

## 주요 기능

### 백엔드
- 상품 관리 API (목록, 상세)
- RAG 파이프라인 (ChromaDB 벡터 검색)
- product_id 범위 제한 검색

### 프론트엔드
- 상품 목록 페이지
- 상품 상세 페이지
- 챗봇 레이어 UI (모달)
- 대화 히스토리 및 소스 표시

## 프로젝트 구조

```
chatbot-fullstack/
├── backend/                    # FastAPI 백엔드
│   ├── main.py                # 앱 엔트리포인트
│   ├── api/                   # API 라우터
│   │   ├── products.py       # 상품 API
│   │   └── chat.py           # 챗봇 API
│   ├── db/                    # 데이터베이스
│   │   ├── database.py       # SQLite 연결 및 초기화
│   │   └── repository.py     # 데이터 조회
│   ├── rag/                   # RAG 파이프라인
│   │   ├── embedder.py       # 임베딩 생성
│   │   ├── chunker.py        # 텍스트 청킹
│   │   ├── vector_store.py   # ChromaDB 관리
│   │   └── retriever.py      # 검색 파이프라인
│   ├── llm/                   # LLM 엔진
│   │   ├── prompt.py         # 공통 프롬프트
│   │   ├── gemini_engine.py  # Gemini API
│   │   └── engine.py         # 엔진 통합
│   ├── requirements.txt       # Python 의존성
│   ├── env.example           # 환경 변수 예시
│   └── README.md             # 백엔드 문서
│
├── frontend/                   # React 프론트엔드
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts     # API 클라이언트
│   │   ├── pages/
│   │   │   ├── Products.tsx  # 상품 목록
│   │   │   └── ProductDetail.tsx  # 상품 상세
│   │   ├── components/
│   │   │   └── ChatBotPanel.tsx   # 챗봇 UI
│   │   ├── App.tsx           # 메인 앱
│   │   └── main.tsx          # 엔트리포인트
│   ├── package.json
│   ├── vite.config.ts
│   ├── env.example           # 환경 변수 예시
│   └── README.md             # 프론트엔드 문서
│
└── README.md                   # 이 파일
```

## 빠른 시작

### 사전 요구사항

- **Python**: 3.9 이상
- **Node.js**: 18 이상

### 1. 백엔드 설정 및 실행

```bash
# 1. 백엔드 디렉토리로 이동
cd backend

# 2. Python 가상환경 생성 및 활성화
# 방법 A: venv (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 방법 B: conda
# conda create -n chatbot-backend python=3.10 -y
# conda activate chatbot-backend

# 3. 의존성 설치
# 중요: pip/uvicorn을 PATH에서 찾지 말고, "venv 파이썬"으로 명시 실행하세요.
./venv/bin/python -m pip install -r requirements.txt

# 4. 환경 변수 설정
cp env.example .env
# .env 파일을 열어 GEMINI_API_KEY 설정 (필수)

# 5. (필수) 개발용 데이터/인덱스 준비
./venv/bin/python -m worker.bootstrap_dev --clear

# 6. 서버 실행
./venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**첫 실행 시**:
- `python -m worker.bootstrap_dev`가 SQLite 생성 + 더미 데이터 시드 + ChromaDB 인덱싱을 한 번에 수행합니다.
- 이후에는 필요할 때만 부트스트랩/인덱싱 명령을 다시 실행하세요.

백엔드 서버: http://localhost:8000
API 문서: http://localhost:8000/docs

### 2. 프론트엔드 설정 및 실행

**새 터미널 창에서**:

```bash
# 1. 프론트엔드 디렉토리로 이동
cd frontend

# 2. 의존성 설치
npm install

# 3. 환경 변수 설정 (선택사항, 기본값 사용 가능)
cp env.example .env

# 4. 개발 서버 실행
npm run dev
```

프론트엔드 서버: http://localhost:5173

## 환경 변수 설정

### 백엔드 (`.env`)

**필수**:
```env
# Gemini API 키 (Gemini 엔진 사용 시 필수)
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

**선택사항**:
```env
# Hugging Face 토큰 (공개 모델은 불필요)
HF_TOKEN=your_huggingface_token_here

# 데이터베이스 경로
DATABASE_PATH=./data/chatbot.db
CHROMA_PERSIST_DIR=./data/chroma
```

**보안 주의사항**:
- `.env` 파일은 절대 Git에 커밋하지 마세요
- API 키는 소스 코드에 하드코딩하지 마세요
- Gemini API 키는 [Google AI Studio](https://makersuite.google.com/app/apikey)에서 발급

### 프론트엔드 (`.env`)

**선택사항** (기본값 사용 가능):
```env
VITE_API_BASE_URL=http://localhost:8000
```

## 사용 방법

### 1. 상품 목록 페이지
1. http://localhost:5173 접속
2. 상품 카드 확인
3. 원하는 상품 클릭

### 2. 상품 상세 페이지
1. 상품 정보, 리뷰, Q&A 확인
2. "AI 챗봇에게 물어보기" 버튼 클릭

### 3. 챗봇 사용
1. **질문 입력**:
   - "이 제품의 배터리는 얼마나 가나요?"
   - "방수 기능이 있나요?"
   - "다른 사용자들의 평가는 어떤가요?"

2. **답변 확인**:
   - AI가 상품 데이터를 기반으로 답변
   - "참고한 정보" 클릭하여 출처 확인

## 트러블슈팅

### 백엔드 오류

#### 1. 로컬 모델 로드 실패
```
로컬 모델 로드 실패
```
**해결**:
- 인터넷 연결 확인
- 디스크 공간 확인 (10GB 이상)
- Gemini 엔진으로 대체 사용

#### 2. Gemini API 오류
```
Gemini API가 초기화되지 않았습니다
```
**해결**:
- `.env` 파일의 `GEMINI_API_KEY` 확인
- API 키 유효성 확인

### 프론트엔드 오류

#### 1. 백엔드 연결 실패
```
네트워크 오류: Failed to fetch
```
**해결**:
- 백엔드 서버 실행 확인 (http://localhost:8000/health)
- CORS 설정 확인

#### 2. 챗봇 응답 오류
**해결**:
- 선택한 엔진이 백엔드에서 사용 가능한지 확인
- 백엔드 로그 확인

## 시스템 요구사항

### 최소 사양 (Gemini 엔진만 사용)
- CPU: 2코어 이상
- RAM: 4GB
- 디스크: 1GB

## 추가 문서

- [백엔드 상세 문서](backend/README.md)
- [프론트엔드 상세 문서](frontend/README.md)
- [Conda 설치 가이드](backend/INSTALL_CONDA.md) (conda 사용자용)
- [API 문서](http://localhost:8000/docs) (서버 실행 후)

## 테스트

### 백엔드 테스트
```bash
# 헬스체크
curl http://localhost:8000/health

# 상품 목록
curl http://localhost:8000/products

# 챗봇 (Gemini)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "배터리는 얼마나 가나요?", "product_id": 1, "engine": "gemini"}'
```

### 프론트엔드 테스트
1. 브라우저에서 http://localhost:5173 접속
2. 상품 목록 → 상품 상세 → 챗봇 순서로 테스트

## 학습 포인트

이 프로젝트를 통해 다음을 학습할 수 있습니다:

1. **RAG 파이프라인 구현**
   - 텍스트 청킹 및 임베딩
   - 벡터 데이터베이스 (ChromaDB) 사용
   - 유사도 검색 및 컨텍스트 주입

2. **LLM 통합**
   - Gemini API 사용
   - 로컬 LLM (Transformers) 로드 및 추론
   - 디바이스 자동 선택 (CUDA/MPS/CPU)

3. **풀스택 개발**
   - FastAPI 백엔드 구축
   - React + TypeScript 프론트엔드
   - API 설계 및 연동

4. **보안 및 환경 설정**
   - 환경 변수 관리
   - API 키 보안
   - CORS 설정

## 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.

## 기여

이슈 및 풀 리퀘스트를 환영합니다!

---

**Happy Coding!**
