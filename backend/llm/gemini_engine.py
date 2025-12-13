"""
Gemini API 엔진
- Google Generative AI 사용
- API 키는 환경 변수에서 로드
"""
import os
import logging
import json
import urllib.request
import urllib.error
import time
from typing import Optional

# google-generativeai는 선택 의존성일 수 있으므로, import 실패 시에도
# 서버가 기동될 수 있도록 방어적으로 처리합니다.
try:
    import google.generativeai as genai  # type: ignore
except Exception as _e:  # pragma: no cover
    genai = None  # type: ignore
    _GENAI_IMPORT_ERROR = _e
else:
    _GENAI_IMPORT_ERROR = None

logger = logging.getLogger(__name__)

# Gemini 모델
_gemini_model = None
_gemini_model_name: Optional[str] = None
_gemini_api_key: Optional[str] = None
_use_rest_fallback: bool = False


def _mask_key(key: str) -> str:
    """로그/에러에 키가 노출되지 않도록 마스킹"""
    if not key:
        return ""
    if len(key) <= 6:
        return "***"
    return f"{key[:3]}***{key[-3:]}"


def _rest_generate_content(prompt: str) -> str:
    """
    google-generativeai 패키지가 없을 때 REST로 Gemini 호출.
    - 표준 라이브러리(urllib)만 사용해 추가 의존성 없이 동작합니다.
    """
    if not _gemini_api_key or not _gemini_model_name:
        raise RuntimeError("Gemini REST 호출에 필요한 설정이 없습니다. GEMINI_API_KEY/GEMINI_MODEL을 확인해주세요.")

    # Generative Language API (v1beta)
    # https://ai.google.dev/api/rest/v1beta/models/generateContent
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{_gemini_model_name}:generateContent?key={_gemini_api_key}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.9,
            "maxOutputTokens": 1024,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    last_http_error: Optional[urllib.error.HTTPError] = None
    # 429/503 등 일시적 오류는 짧게 재시도
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                break
        except urllib.error.HTTPError as e:
            last_http_error = e
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                body = ""

            # rate limit / 일시 장애는 백오프 후 재시도
            if e.code in (429, 503) and attempt < 2:
                wait_s = 1.0 * (2**attempt)
                logger.warning(f"Gemini REST 일시 오류(status={e.code}) → {wait_s:.1f}s 후 재시도")
                time.sleep(wait_s)
                continue

            # 최종 실패: 원인별로 메시지 분기 (키는 절대 로그/메시지에 포함하지 않음)
            msg = "Gemini API 호출이 실패했습니다."
            if e.code == 429:
                msg = (
                    "Gemini API 호출이 429(Quota/Rate limit)으로 실패했습니다. "
                    "현재 키/프로젝트의 할당량이 0이거나 초과된 상태입니다. "
                    "Google AI Studio의 Usage/Rate limit에서 쿼터를 확인하고(필요 시 Billing/플랜 설정), "
                    "올바른 Gemini API Key를 사용해주세요."
                )
            elif e.code == 403:
                msg = (
                    "Gemini API 호출이 403(Permission)으로 실패했습니다. "
                    "API 키 제한(허용 API/리퍼러/IP) 또는 Generative Language API 비활성화 가능성이 큽니다."
                )
            elif e.code == 404:
                msg = (
                    "Gemini API 호출이 404(Not found)로 실패했습니다. "
                    "GEMINI_MODEL 값(모델명)을 확인해주세요."
                )
            elif e.code == 400:
                msg = (
                    "Gemini API 호출이 400(Bad request)로 실패했습니다. "
                    "프롬프트/요청 포맷 또는 generationConfig를 확인해주세요."
                )

            logger.error(f"Gemini REST HTTPError: status={e.code}, body={body[:500]}")
            raise RuntimeError(msg) from e
        except Exception as e:
            logger.error(f"Gemini REST 호출 실패: {str(e)}")
            raise RuntimeError("Gemini API 호출 중 오류가 발생했습니다.") from e
    else:
        # for-else 방지용 (실제로는 위에서 raise/continue 처리)
        raise RuntimeError("Gemini API 호출이 실패했습니다.") from last_http_error

    try:
        obj = json.loads(raw)
    except Exception as e:
        logger.error(f"Gemini REST 응답 JSON 파싱 실패: {raw[:500]}")
        raise RuntimeError("Gemini API 응답을 처리하지 못했습니다.") from e

    # 응답 스키마: candidates[0].content.parts[0].text
    candidates = obj.get("candidates") or []
    if not candidates:
        # safety block 등으로 비어있을 수 있음
        logger.warning(f"Gemini REST 응답에 candidates가 없습니다: {str(obj)[:500]}")
        raise RuntimeError("Gemini가 답변을 생성하지 못했습니다.")

    content = (candidates[0].get("content") or {})
    parts = content.get("parts") or []
    if not parts:
        logger.warning(f"Gemini REST 응답에 parts가 없습니다: {str(obj)[:500]}")
        raise RuntimeError("Gemini가 답변을 생성하지 못했습니다.")

    text = parts[0].get("text")
    if not text:
        raise RuntimeError("Gemini 응답 텍스트가 비어 있습니다.")
    return str(text)


def init_gemini():
    """Gemini API 초기화"""
    global _gemini_model, _gemini_model_name, _gemini_api_key, _use_rest_fallback

    if _gemini_model is not None:
        logger.info("Gemini 모델 이미 초기화됨")
        return
    
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    _gemini_api_key = api_key
    _gemini_model_name = model_name
    
    if not api_key:
        logger.warning("GEMINI_API_KEY가 설정되지 않았습니다")
        logger.warning("Gemini 엔진을 사용하려면 .env 파일에 API 키를 설정해주세요")
        return

    # google-generativeai가 있으면 SDK 사용, 없으면 REST 폴백
    if genai is None:
        _use_rest_fallback = True
        logger.warning("google-generativeai 패키지가 설치되지 않았습니다")
        logger.warning("SDK 대신 REST 폴백으로 Gemini를 사용합니다")
        logger.info(f"Gemini REST 폴백 준비 완료 (model={model_name}, key={_mask_key(api_key)})")
        return

    try:
        logger.info("Gemini API 초기화 중...")
        genai.configure(api_key=api_key)

        _use_rest_fallback = False
        _gemini_model = genai.GenerativeModel(model_name)
        logger.info(f"Gemini API 초기화 완료 (model={model_name})")
    except Exception as e:
        logger.error(f"Gemini 초기화 실패: {str(e)}")
        logger.warning("SDK 초기화 실패 → REST 폴백으로 전환합니다")
        _use_rest_fallback = True


async def generate_gemini(prompt: str) -> str:
    """
    Gemini API로 텍스트 생성
    
    Args:
        prompt: 입력 프롬프트
        
    Returns:
        생성된 텍스트
    """
    # SDK가 없거나 초기화 실패 시 REST 폴백 사용
    if _use_rest_fallback or genai is None or _gemini_model is None:
        return _rest_generate_content(prompt)
    
    try:
        # Gemini API 호출
        response = _gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=1024,
            )
        )
        
        return response.text
        
    except Exception as e:
        logger.error(f"Gemini 생성 실패: {str(e)}")
        # SDK 호출 실패 시에도 REST 폴백 시도 (가능하면)
        if _gemini_api_key and _gemini_model_name:
            logger.warning("SDK 호출 실패 → REST 폴백을 시도합니다")
            return _rest_generate_content(prompt)
        raise RuntimeError("Gemini API 호출 중 오류가 발생했습니다.") from e


def is_gemini_available() -> bool:
    """Gemini API 사용 가능 여부 확인"""
    # SDK든 REST든, 최소한 API 키가 있어야 사용 가능
    if _gemini_api_key:
        return True
    return genai is not None and _gemini_model is not None

