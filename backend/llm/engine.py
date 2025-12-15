"""
LLM 엔진 통합 인터페이스
- Gemini 엔진 단일 사용
- 공통 인터페이스 제공
"""
import logging
from llm.gemini_engine import init_gemini, generate_gemini, is_gemini_available

logger = logging.getLogger(__name__)


async def init_llm_engines():
    """
    모든 LLM 엔진 초기화
    - Gemini API 초기화
    """
    logger.info("LLM 엔진 초기화 시작...")
    
    # Gemini 초기화
    init_gemini()
    
    # 사용 가능한 엔진 확인
    available_engines = []
    if is_gemini_available():
        available_engines.append("gemini")
    
    if not available_engines:
        logger.error("사용 가능한 LLM 엔진이 없습니다")
        logger.error("Gemini API 키 및 패키지 설정을 확인해주세요")
    else:
        logger.info(f"사용 가능한 엔진: {', '.join(available_engines)}")


async def generate_answer(prompt: str, engine: str = "gemini") -> str:
    """
    LLM으로 답변 생성 (엔진 선택)
    
    Args:
        prompt: 입력 프롬프트
        engine: 사용할 엔진 ('gemini')
        
    Returns:
        생성된 답변
    """
    if engine != "gemini":
        raise ValueError(f"지원하지 않는 엔진: {engine}")

    if not is_gemini_available():
        raise RuntimeError(
            "Gemini API를 사용할 수 없습니다. "
            "google-generativeai 설치 및 .env의 GEMINI_API_KEY 설정을 확인해주세요."
        )
    return await generate_gemini(prompt)


def get_available_engines() -> dict:
    """사용 가능한 엔진 목록 반환"""
    return {
        "gemini": is_gemini_available()
    }

