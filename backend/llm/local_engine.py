"""
로컬 LLM 엔진 (Transformers + PyTorch)
- beomi/gemma-ko-2b 모델 사용
- 디바이스 자동 선택: cuda → mps → cpu
- Hugging Face 캐시 활용
"""
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import logging
from typing import Optional
import sys

logger = logging.getLogger(__name__)

# 전역 모델 및 토크나이저
_local_model = None
_local_tokenizer = None
_device = None


def select_device() -> str:
    """
    사용 가능한 디바이스 선택 (cuda → mps → cpu)
    
    Returns:
        디바이스 문자열 ('cuda', 'mps', 'cpu')
    """
    if torch.cuda.is_available():
        device = "cuda"
        logger.info(f"CUDA 사용 가능: {torch.cuda.get_device_name(0)}")
    elif torch.backends.mps.is_available():
        device = "mps"
        logger.info("MPS (Apple Silicon) 사용 가능")
    else:
        device = "cpu"
        logger.info("CPU 사용")
    
    return device


def init_local_model():
    """
    로컬 LLM 모델 초기화
    - Hugging Face에서 모델 다운로드 (캐시 활용)
    - 디바이스 자동 선택
    """
    global _local_model, _local_tokenizer, _device
    
    if _local_model is not None:
        logger.info("로컬 모델 이미 로드됨")
        return
    
    try:
        # 어떤 파이썬/transformers로 실행 중인지 로그로 고정 출력 (환경 꼬임 진단용)
        runtime_py = sys.executable
        runtime_tf = "unknown"
        try:
            import transformers  # type: ignore
            runtime_tf = str(getattr(transformers, "__version__", "unknown"))

            # 기본은 INFO로 출력하고,
            # venv가 아닌 Python으로 실행 중이거나(예: mise/miniforge),
            # transformers가 낮아 GemmaTokenizer가 없을 가능성이 크면 WARNING으로 올립니다.
            is_venv_python = ("venv/bin/python" in runtime_py) or ("venv\\Scripts\\python" in runtime_py)
            try:
                major, minor, patch = (int(x) for x in runtime_tf.split(".", 2))
            except Exception:
                major, minor, patch = (0, 0, 0)
            tf_too_old_for_gemma = (major, minor, patch) < (4, 49, 0)

            level = logging.INFO if (is_venv_python and not tf_too_old_for_gemma) else logging.WARNING
            logger.log(level, f"sys.executable = {runtime_py}")
            logger.log(level, f"transformers = {runtime_tf}")
        except Exception as _e:
            logger.warning(f"transformers 버전 확인 실패: {str(_e)}")

        # 환경 변수에서 모델 ID 가져오기
        model_id = os.getenv("LOCAL_MODEL_ID", "beomi/gemma-ko-2b")
        
        logger.info(f"로컬 LLM 모델 로드 중: {model_id}")
        logger.info("첫 실행 시 모델 다운로드로 시간이 걸릴 수 있습니다...")
        
        # 디바이스 선택
        _device = select_device()
        
        # 토크나이저 로드
        logger.info("토크나이저 로드 중...")
        try:
            _local_tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True,
                use_fast=True,
                local_files_only=False,
            )
        except Exception as e:
            # 일부 모델/환경에서는 fast tokenizer가 없거나 호환 문제가 있을 수 있어 fallback 시도
            logger.warning(f"fast tokenizer 로드 실패 → slow tokenizer로 재시도: {str(e)}")
            _local_tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True,
                use_fast=False,
                local_files_only=False,
            )
        
        # 모델 로드
        logger.info(f"모델 로드 중 (디바이스: {_device})...")
        _local_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if _device != "cpu" else torch.float32,
            device_map=_device if _device == "cuda" else None,
            trust_remote_code=True,
            local_files_only=False,
        )
        
        # CPU나 MPS인 경우 수동으로 디바이스 이동
        if _device in ["cpu", "mps"]:
            _local_model = _local_model.to(_device)
        
        _local_model.eval()  # 추론 모드
        
        logger.info(f"로컬 LLM 모델 로드 완료: {model_id} on {_device}")
        
    except Exception as e:
        logger.error(f"로컬 모델 로드 실패: {str(e)}")
        logger.error(f"런타임 정보: sys.executable={runtime_py}, transformers={runtime_tf}")
        # Gemma 계열에서 흔한 원인: transformers 버전이 낮아 GemmaTokenizer가 없음
        if "GemmaTokenizer" in str(e):
            logger.error(
                "해결: transformers 버전을 Gemma 지원 버전으로 업그레이드하세요. "
                "(예: transformers>=4.5x)"
            )
            logger.error(
                "추가 점검: 현재 서버가 venv가 아닌 다른 Python(예: mise/miniforge)으로 실행 중이면 "
                "업그레이드가 반영되지 않습니다. `./venv/bin/python -m uvicorn ...`로 실행하세요."
            )
        logger.warning("로컬 엔진을 사용할 수 없습니다. Gemini 엔진을 사용해주세요")
        # 모델 로드 실패 시 None으로 유지 (fallback 처리)


async def generate_local(prompt: str, max_length: int = 256) -> str:
    """
    로컬 LLM으로 텍스트 생성
    
    Args:
        prompt: 입력 프롬프트
        max_length: 최대 생성 길이
        
    Returns:
        생성된 텍스트
    """
    if _local_model is None or _local_tokenizer is None:
        raise RuntimeError(
            "로컬 모델이 로드되지 않았습니다. "
            "모델 로드에 실패했거나 초기화되지 않았습니다. "
            "Gemini 엔진을 사용하거나 서버를 재시작해주세요."
        )
    
    try:
        # 토큰화
        inputs = _local_tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1024
        ).to(_device)
        
        # 생성
        with torch.no_grad():
            outputs = _local_model.generate(
                **inputs,
                max_new_tokens=max_length,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=_local_tokenizer.eos_token_id
            )
        
        # 디코딩
        generated_text = _local_tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        )
        
        # 프롬프트 부분 제거하고 답변만 추출
        if prompt in generated_text:
            answer = generated_text.replace(prompt, "").strip()
        else:
            answer = generated_text.strip()
        
        return answer
        
    except Exception as e:
        logger.error(f"로컬 생성 실패: {str(e)}")
        raise RuntimeError(f"로컬 LLM 생성 중 오류 발생: {str(e)}")


def is_local_model_available() -> bool:
    """로컬 모델 사용 가능 여부 확인"""
    return _local_model is not None and _local_tokenizer is not None

