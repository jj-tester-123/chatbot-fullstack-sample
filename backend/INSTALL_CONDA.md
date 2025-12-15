# Conda 환경 설치 가이드

conda를 사용하여 백엔드를 설치하는 상세 가이드입니다.

## 1. Conda 설치 확인

```bash
conda --version
```

conda가 설치되어 있지 않다면:
- **Miniconda**: https://docs.conda.io/en/latest/miniconda.html (권장, 가벼움)
- **Anaconda**: https://www.anaconda.com/download (전체 패키지 포함)

## 2. Conda 가상환경 생성

```bash
cd backend

# Python 3.10 환경 생성 (권장)
conda create -n chatbot-backend python=3.10 -y

# 또는 Python 3.11
# conda create -n chatbot-backend python=3.11 -y
```

## 3. 환경 활성화

```bash
conda activate chatbot-backend
```

활성화 확인:
```bash
which python  # conda 환경 경로가 나와야 함
python --version  # Python 3.10.x 또는 3.11.x
```

## 4. 의존성 설치

```bash
pip install -r requirements.txt
```

**참고**: conda 환경에서도 `pip`를 사용하여 패키지를 설치합니다.

## 5. PyTorch 설치 (선택사항: GPU 사용 시)

### CUDA (NVIDIA GPU)
```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### MPS (Apple Silicon)
```bash
# 기본 설치로 MPS 자동 지원
pip install torch torchvision torchaudio
```

### CPU only
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

## 6. 환경 변수 설정

```bash
cp env.example .env
# .env 파일을 열어 GEMINI_API_KEY 설정 (필요 시 GEMINI_MODEL도 변경)
```

## 7. 서버 실행

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Conda 환경 관리

### 환경 목록 확인
```bash
conda env list
```

### 환경 비활성화
```bash
conda deactivate
```

### 환경 삭제 (필요시)
```bash
conda remove -n chatbot-backend --all
```

### 환경 내보내기 (공유용)
```bash
conda env export > environment.yml
```

### 환경 가져오기 (공유받은 경우)
```bash
conda env create -f environment.yml
```

## venv vs conda 비교

| 특징 | venv | conda |
|------|------|-------|
| 설치 | Python 내장 | 별도 설치 필요 |
| 속도 | 빠름 | 느림 |
| 패키지 관리 | pip만 | pip + conda |
| 과학 라이브러리 | 수동 설치 | 최적화된 빌드 |
| Python 버전 관리 | 불가 | 가능 |
| 권장 사용 | 일반 웹 개발 | 데이터 사이언스, ML |

## 트러블슈팅

### conda activate가 작동하지 않아요
```bash
# conda 초기화
conda init bash  # 또는 zsh, fish 등
# 터미널 재시작 후 다시 시도
```

### 패키지 충돌 오류
```bash
# 환경 삭제 후 재생성
conda remove -n chatbot-backend --all
conda create -n chatbot-backend python=3.10 -y
conda activate chatbot-backend
pip install -r requirements.txt
```

### pip가 conda 환경 외부에 설치되는 문제
```bash
# 환경 활성화 확인
conda activate chatbot-backend
which pip  # conda 환경 경로가 나와야 함

# conda 환경의 pip 사용 강제
python -m pip install -r requirements.txt
```

## 추가 정보

- [Conda 공식 문서](https://docs.conda.io/)
- [Conda Cheat Sheet](https://docs.conda.io/projects/conda/en/latest/user-guide/cheatsheet.html)

