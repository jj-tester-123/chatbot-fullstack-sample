# 🚀 빠른 시작 가이드

이 가이드를 따라하면 **5분 안에** 챗봇 애플리케이션을 로컬에서 실행할 수 있습니다.

## ⚡ 최소 설정으로 바로 시작하기

### 1단계: 백엔드 준비 (2분)

```bash
# 터미널 1
cd backend

# 가상환경 생성 (venv 또는 conda 중 선택)
# 방법 A: venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 방법 B: conda
# conda create -n chatbot-backend python=3.10 -y
# conda activate chatbot-backend

pip install -r requirements.txt

# .env 파일 생성 및 Gemini API 키 설정
cp env.example .env
# .env 파일을 열어 GEMINI_API_KEY=your_key_here 입력

```

### 1.5단계: (필수) 더미 데이터 + RAG 인덱스 부트스트랩

백엔드는 실행 시 DB를 자동 시드/인덱싱하지 않습니다.
아래 명령으로 **DB 초기화 → 더미 데이터 시드 → RAG 인덱싱**을 한 번에 수행하세요.

```bash
cd backend
python -m worker.bootstrap_dev --clear

# 컬렉션을 지우지 않고 upsert만 하고 싶다면
# python -m worker.bootstrap_dev --no-clear
```

### 1.6단계: 백엔드 서버 실행

```bash
cd backend
uvicorn main:app --reload
```

✅ 백엔드 준비 완료: http://localhost:8000

### 2단계: 프론트엔드 실행 (1분)

```bash
# 터미널 2 (새 터미널 창)
cd frontend
npm install
npm run dev
```

✅ 프론트엔드 준비 완료: http://localhost:5173

### 3단계: 브라우저에서 확인

1. http://localhost:5173 접속
2. 상품 클릭
3. "🤖 AI 챗봇에게 물어보기" 버튼 클릭
4. 질문 입력 (예: "배터리는 얼마나 가나요?")

## 🔑 Gemini API 키 발급 (1분)

1. https://makersuite.google.com/app/apikey 접속
2. "Create API Key" 클릭
3. 생성된 키를 복사
4. `backend/.env` 파일에 붙여넣기

```env
GEMINI_API_KEY=AIzaSy...여기에_키_붙여넣기
```

## 🎯 첫 실행 시 주의사항

### 백엔드 첫 실행 (약 2~3분 소요)
- ✅ `python -m worker.bootstrap_dev` 실행 시 SQLite 생성 및 더미 데이터 삽입
- ✅ 같은 명령으로 ChromaDB 벡터 인덱싱 수행 (기본: --clear)
- ✅ 임베딩 모델 다운로드 (최초 1회, 약 500MB)

## ✅ 정상 작동 확인

### 백엔드 확인
```bash
curl http://localhost:8000/health
# 응답: {"status":"healthy",...}
```

### 프론트엔드 확인
- 브라우저에서 상품 목록이 보이면 성공!

## 🔧 문제 해결

### 백엔드가 시작되지 않아요
```bash
# Python 버전 확인 (3.9 이상 필요)
python --version

# 가상환경 활성화 확인
which python  # venv 또는 conda 환경 경로가 나와야 함

# venv 사용 시
source venv/bin/activate

# conda 사용 시
conda activate chatbot-backend
```

### Gemini API 오류
```
❌ Gemini API가 초기화되지 않았습니다
```
→ `.env` 파일의 `GEMINI_API_KEY` 확인

### 프론트엔드가 백엔드에 연결되지 않아요
```
네트워크 오류: Failed to fetch
```
→ 백엔드가 실행 중인지 확인 (http://localhost:8000/health)

### 로컬 LLM이 너무 느려요
→ 로컬 LLM은 사용하지 않습니다. Gemini만 사용하세요.

## 📚 다음 단계

- [전체 문서 보기](README.md)
- [백엔드 상세 가이드](backend/README.md)
- [프론트엔드 상세 가이드](frontend/README.md)

## 💡 팁

### 가상환경 선택: venv vs conda
- **venv (권장)**: Python 내장, 빠르고 가벼움
- **conda**: 데이터 사이언스/ML 작업 시 편리, Python 버전 관리 용이
- **상세 가이드**: [Conda 설치 가이드](backend/INSTALL_CONDA.md)

### Gemini만 사용하기 (권장)
- Gemini만 사용합니다.

### 개발 모드 vs 프로덕션
- 이 프로젝트는 **로컬 개발 전용**입니다
- 배포는 고려하지 않았으므로, 학습 및 테스트 목적으로만 사용하세요

---

**문제가 있나요?** [전체 문서](README.md)의 트러블슈팅 섹션을 확인하세요!
