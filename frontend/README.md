# RAG 챗봇 프론트엔드 (React + TypeScript)

상품 데이터 기반 RAG 챗봇의 프론트엔드 웹 애플리케이션입니다.

## 🚀 주요 기능

- **상품 목록 페이지**: 모든 상품을 카드 형식으로 표시
- **상품 상세 페이지**: 상품 정보 및 리뷰, Q&A 표시
- **AI 챗봇 레이어**: 상품에 대한 질문을 AI에게 물어볼 수 있는 대화형 UI
- **LLM 엔진 선택**: Gemini API ↔ 로컬 LLM 실시간 전환
- **소스 표시**: AI 답변의 근거가 된 정보 출처 표시

## 📁 프로젝트 구조

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts          # 백엔드 API 클라이언트
│   ├── pages/
│   │   ├── Products.tsx       # 상품 목록 페이지
│   │   ├── Products.css
│   │   ├── ProductDetail.tsx  # 상품 상세 페이지
│   │   └── ProductDetail.css
│   ├── components/
│   │   ├── ChatBotPanel.tsx   # 챗봇 레이어 UI
│   │   └── ChatBotPanel.css
│   ├── App.tsx                # 메인 앱 (라우팅)
│   ├── App.css
│   └── main.tsx               # 엔트리포인트
├── public/                     # 정적 파일
├── package.json
├── vite.config.ts             # Vite 설정
├── tsconfig.json
└── README.md                  # 이 파일
```

## 🛠️ 설치 및 실행

### 1. 의존성 설치

```bash
cd frontend
npm install
```

### 2. 환경 변수 설정 (선택사항)

`env.example`을 복사하여 `.env` 파일을 생성합니다.

```bash
cp env.example .env
```

`.env` 파일 편집 (기본값 사용 시 생략 가능):

```env
# 백엔드 API URL (기본값: http://localhost:8000)
VITE_API_BASE_URL=http://localhost:8000
```

### 3. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 http://localhost:5173 접속

### 4. 프로덕션 빌드

```bash
npm run build
npm run preview
```

## 📡 백엔드 연동

프론트엔드는 백엔드 API와 통신하여 데이터를 가져옵니다.

**백엔드 서버가 먼저 실행되어 있어야 합니다!**

백엔드 실행 방법은 `../backend/README.md`를 참고하세요.

### API 프록시 설정

`vite.config.ts`에서 프록시 설정이 되어 있어 CORS 문제 없이 개발할 수 있습니다:

```typescript
server: {
  port: 5173,
  proxy: {
    '/products': 'http://localhost:8000',
    '/chat': 'http://localhost:8000',
  }
}
```

## 🎨 화면 구성

### 1. 상품 목록 페이지 (`/products`)

- 모든 상품을 그리드 형식으로 표시
- 각 상품 카드에는 이미지, 이름, 카테고리, 가격, 설명 포함
- 상품 클릭 시 상세 페이지로 이동

### 2. 상품 상세 페이지 (`/products/:id`)

- 상품 기본 정보 (이미지, 이름, 가격, 설명)
- 상세 설명, 고객 리뷰, Q&A 섹션
- "AI 챗봇에게 물어보기" 버튼

### 3. 챗봇 레이어 (모달)

- 상품 상세 페이지에서 버튼 클릭 시 오버레이로 표시
- **LLM 엔진 선택**: Gemini (클라우드) ↔ 로컬 LLM (Gemma-ko-2b)
- **질문 입력**: 텍스트 입력창
- **대화 히스토리**: 사용자 질문과 AI 응답 표시
- **소스 표시**: 답변의 근거가 된 정보 출처 (접기/펼치기)

## 🤖 챗봇 사용 가이드

### 엔진 선택

챗봇 상단의 드롭다운에서 LLM 엔진을 선택할 수 있습니다:

#### Gemini (클라우드)
- **장점**: 빠른 응답, 높은 품질
- **단점**: 인터넷 연결 필요, 백엔드에 API 키 설정 필요
- **권장 시나리오**: 일반적인 사용

#### 로컬 LLM (Gemma-ko-2b)
- **장점**: 오프라인 사용 가능, 비용 없음
- **단점**: 느린 응답, 백엔드에 모델 다운로드 필요
- **권장 시나리오**: 오프라인 환경, 데이터 보안 중요

### 질문 예시

상품에 대해 다음과 같은 질문을 할 수 있습니다:

- "이 제품의 주요 특징은 무엇인가요?"
- "배터리는 얼마나 가나요?"
- "방수 기능이 있나요?"
- "다른 사용자들의 평가는 어떤가요?"
- "아이폰과 호환되나요?"

### 소스 확인

AI 답변 아래의 "📚 참고한 정보" 섹션을 클릭하면:
- 답변 생성에 사용된 원본 텍스트 확인 가능
- 각 소스의 타입 (description/review/qna) 표시
- 관련도 점수 (%) 표시

## 🔧 트러블슈팅

### 1. 백엔드 연결 오류

```
네트워크 오류: Failed to fetch
```

**해결 방법**:
- 백엔드 서버가 실행 중인지 확인 (http://localhost:8000/health)
- `.env` 파일의 `VITE_API_BASE_URL` 확인
- CORS 설정 확인 (백엔드 `main.py`)

### 2. 챗봇 응답 오류

```
죄송합니다. 오류가 발생했습니다: ...
```

**해결 방법**:
- 선택한 엔진이 백엔드에서 사용 가능한지 확인
  - Gemini: API 키 설정 확인
  - 로컬: 모델 다운로드 완료 확인
- 백엔드 로그 확인

### 3. 빌드 오류

```
Module not found: Error: Can't resolve 'react-router-dom'
```

**해결 방법**:
```bash
npm install
```

## 🎨 커스터마이징

### 스타일 변경

각 컴포넌트의 `.css` 파일을 수정하여 스타일을 변경할 수 있습니다:

- `Products.css`: 상품 목록 페이지 스타일
- `ProductDetail.css`: 상품 상세 페이지 스타일
- `ChatBotPanel.css`: 챗봇 레이어 스타일

### API 엔드포인트 추가

`src/api/client.ts`에 새로운 API 함수를 추가할 수 있습니다:

```typescript
export async function newApiFunction(): Promise<ResponseType> {
  return fetchApi<ResponseType>('/new-endpoint');
}
```

## 📊 성능 최적화

### 프로덕션 빌드 최적화

```bash
npm run build
```

빌드된 파일은 `dist/` 디렉토리에 생성됩니다.

### 코드 스플리팅

React Router의 `lazy` 로딩을 사용하여 페이지별 코드 스플리팅을 구현할 수 있습니다 (추후 개선 가능).

## 🧪 테스트

### 개발 서버 테스트

1. 백엔드 서버 실행 (http://localhost:8000)
2. 프론트엔드 개발 서버 실행 (http://localhost:5173)
3. 브라우저에서 접속하여 기능 테스트

### 프로덕션 빌드 테스트

```bash
npm run build
npm run preview
```

http://localhost:4173 에서 프로덕션 빌드 테스트

## 📝 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.

## 🤝 기여

이슈 및 풀 리퀘스트를 환영합니다!
