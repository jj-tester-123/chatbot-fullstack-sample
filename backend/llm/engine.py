"""
LLM 엔진 통합 인터페이스
- Gemini와 로컬 LLM 스위칭
- 공통 인터페이스 제공
"""
import logging
from llm.gemini_engine import init_gemini, generate_gemini, is_gemini_available
from llm.local_engine import init_local_model, generate_local, is_local_model_available

logger = logging.getLogger(__name__)


async def init_llm_engines():
    """
    모든 LLM 엔진 초기화
    - Gemini API 초기화
    - 로컬 모델 로드
    """
    logger.info("LLM 엔진 초기화 시작...")
    
    # Gemini 초기화
    init_gemini()
    
    # 로컬 모델 초기화
    init_local_model()
    
    # 사용 가능한 엔진 확인
    available_engines = []
    if is_gemini_available():
        available_engines.append("gemini")
    if is_local_model_available():
        available_engines.append("local")
    
    if not available_engines:
        logger.error("사용 가능한 LLM 엔진이 없습니다")
        logger.error("Gemini API 키를 설정하거나 로컬 모델 로드를 확인해주세요")
    else:
        logger.info(f"사용 가능한 엔진: {', '.join(available_engines)}")


async def generate_answer(prompt: str, engine: str = "gemini") -> str:
    """
    LLM으로 답변 생성 (엔진 선택)
    
    Args:
        prompt: 입력 프롬프트
        engine: 사용할 엔진 ('gemini' 또는 'local')
        
    Returns:
        생성된 답변
    """
    if engine == "gemini":
        if not is_gemini_available():
            # 개발/배포 환경에서 google-generativeai가 없거나 API 키가 없는 경우가 있으므로
            # 가능한 경우 로컬 엔진으로 자동 폴백합니다.
            if is_local_model_available():
                logger.warning("Gemini 사용 불가 → 로컬 엔진으로 폴백합니다")
                return await generate_local(prompt)

            raise RuntimeError(
                "Gemini API를 사용할 수 없습니다. "
                "google-generativeai 설치 및 .env의 GEMINI_API_KEY 설정을 확인해주세요."
            )
        return await generate_gemini(prompt)
    
    elif engine == "local":
        if not is_local_model_available():
            raise RuntimeError(
                "로컬 모델을 사용할 수 없습니다. "
                "모델 로드에 실패했거나 초기화되지 않았습니다."
            )
        return await generate_local(prompt)
    
    else:
        raise ValueError(f"지원하지 않는 엔진: {engine}")


def get_available_engines() -> dict:
    """사용 가능한 엔진 목록 반환"""
    return {
        "gemini": is_gemini_available(),
        "local": is_local_model_available()
    }

