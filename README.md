# RAG 챗봇 풀스택 (FastAPI + React)

상품 데이터(설명/리뷰/Q&A)를 기반으로 **RAG(Retrieval-Augmented Generation)** 검색과 **LLM(Gemini)** 을 사용해 답변하는 챗봇 웹 애플리케이션입니다.  
이 문서는 **프로젝트 대표 진입점(허브)** 이고, 실행/설정/상세는 백엔드·프론트 문서를 참고합니다.

## 구성

- **Backend**: FastAPI + SQLite + ChromaDB (`backend/`)
- **Frontend**: Vite + React + TypeScript (`frontend/`)
- **LLM**: Gemini API (기본)

## QuickStart (로컬 개발)

### 사전 요구사항

- **Python**: 3.9+
- **Node.js**: 18+

### 1) 백엔드 실행

```bash
cd backend

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

python -m pip install -r requirements.txt

cp env.example .env
# .env에 GEMINI_API_KEY 설정 (필수)

# (필수) DB 초기화 + 더미 데이터 + RAG 인덱스 생성
python -m worker.bootstrap_dev --clear

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- 백엔드: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs`

### 2) 프론트엔드 실행

```bash
cd frontend
npm install
cp env.example .env  # 선택: 기본값 사용 가능
npm run dev
```

- 프론트엔드: `http://localhost:5173`

## 환경 변수 / 보안

- **절대** `.env`를 Git에 커밋하지 마세요.
- API 키(예: `GEMINI_API_KEY`)는 **코드에 하드코딩 금지**입니다.
- 환경 변수 상세는 아래 문서를 참고하세요.
  - 백엔드: `backend/README.md` (### 3. 환경 변수 설정)
  - 프론트엔드: `frontend/README.md` (### 2. 환경 변수 설정)

## 문서

- 백엔드 상세: `backend/README.md`
- 프론트엔드 상세: `frontend/README.md`
- Conda 가이드(선택): `backend/INSTALL_CONDA.md`
