"""[신규 추가 파일] 발표 성장 AI 피드백 (Gemini).

growth_schema.build_growth_report()가 만든 compare_with_previous를 표준화된 프롬프트에 넣어
"성장한 부분 / 개선이 필요한 부분 / 다음 연습 제안"을 생성한다.

- 계획서 리스크 "AI 피드백 일관성": 프롬프트 형식을 고정하고 temperature를 낮춰 일관성을 높인다.
- 계획서 리스크 "지표 변화가 크지 않은 경우": 작은 변화도 '소폭'으로 설명하도록 프롬프트에 명시한다.
- 같은 (사용자, 최신 발표, 직전 발표) 조합은 메모리에 캐시해 그래프 화면을 열 때마다 API를 호출하지 않는다.
- 호출 실패 시 None을 돌려주고, 호출한 쪽(history 라우터)이 규칙 기반 피드백을 그대로 쓴다.

기존 코칭(video_analyzer)이 Gemini REST를 쓰고 있어 같은 방식·같은 설정(gemini_api_key, gemini_model)을 따른다.
"""
import json
import logging
from collections import OrderedDict
from typing import Any
from urllib import request as urlrequest

from app.core.config import settings
from app.services.growth_schema import VERDICT_LABEL

logger = logging.getLogger(__name__)

_CACHE_MAX = 200
_cache: "OrderedDict[tuple, str]" = OrderedDict()

def _model_candidates() -> list[str]:
    configured = settings.gemini_model.strip().removeprefix("models/")
    candidates = [configured, "gemini-flash-latest", "gemini-2.5-flash"]
    return list(dict.fromkeys(model for model in candidates if model))

def build_growth_prompt(compare: dict[str, Any]) -> str:
    rows = []
    for m in compare.get("metrics") or []:
        unit = m["unit"]
        rows.append(
            f"- {m['label']}: 이전 {m['previous']}{unit} → 현재 {m['current']}{unit} "
            f"(변화 {m['delta']:+.1f}{unit}, 판정: {VERDICT_LABEL[m['verdict']]})"
        )
    table = "\n".join(rows) if rows else "- (비교 가능한 지표가 없습니다)"

    total_note = (
        ""
        if compare.get("comparable_by_total")
        else "\n※ 이전 발표와 채점 기준이 달라 총점은 비교 대상에서 제외했습니다. 총점 언급은 하지 마세요.\n"
    )

    return f"""
당신은 발표 코치입니다. 같은 사용자의 '이전 발표'와 '현재 발표'를 비교한 결과를 보고 성장 피드백을 한국어로 작성하세요.

[지표 비교]
{table}
{total_note}
작성 규칙
- 아래 Markdown 템플릿의 제목과 순서를 그대로 유지하세요. 코드블록과 표는 쓰지 마세요.
- 반드시 위 표에 있는 수치만 근거로 쓰고, 표에 없는 사실은 지어내지 마세요.
- 변화가 작더라도(예: 점수 1~2점, 비율 1%p 미만) 무시하지 말고 '소폭 개선/소폭 하락'으로 표현하고 그 의미를 한 줄로 설명하세요.
- 시선 이탈률과 어깨 기울기, 필러워드는 낮을수록 좋고, 제스처 횟수와 발표 속도는 좋고 나쁨을 단정하지 말고 변화만 설명하세요.
- 각 섹션은 최대 3개 항목, 항목당 한 문장으로 쓰세요. 해당하는 내용이 없으면 "- 해당 없음"이라고 쓰세요.

## 성장한 부분
- 좋아진 지표와 그 의미를 설명하세요.

## 개선이 필요한 부분
- 하락했거나 정체된 지표와 그 의미를 설명하세요.

## 다음 연습 제안
- 다음 발표에서 바로 해볼 구체적인 행동 1~2가지를 제안하세요.
""".strip()

def _call_gemini(model_name: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3},  # 피드백 일관성을 위해 낮게 고정
        }
    ).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-goog-api-key": settings.gemini_api_key},
    )
    # [2026-09-22 수정] 타임아웃 25초 -> 12초.
    # 모델 후보가 3개라 최악의 경우 75초 동안 성장 분석 화면이 멈춰 있었다.
    with urlrequest.urlopen(req, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))

    # [2026-09-22 수정] candidates가 빈 배열이어도 IndexError가 나지 않게 한다.
    candidates = payload.get("candidates") or []
    if not candidates:
        logger.warning("Gemini growth feedback returned no candidates")
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "\n".join(part.get("text", "") for part in parts).strip()

def generate_growth_feedback(cache_key: tuple, compare: dict[str, Any]) -> str | None:
    """AI 성장 피드백을 만든다. 키가 없거나 호출이 모두 실패하면 None."""
    if not settings.gemini_api_key or not compare.get("metrics"):
        return None

    if cache_key in _cache:
        _cache.move_to_end(cache_key)
        return _cache[cache_key]

    prompt = build_growth_prompt(compare)
    for model_name in _model_candidates():
        try:
            text = _call_gemini(model_name, prompt)
        # [2026-09-22 수정] 예외 종류를 한정하지 않는다. 실패하면 다음 모델,
        # 전부 실패하면 None을 돌려주고 호출한 쪽이 규칙 기반 피드백을 그대로 쓴다.
        except Exception as exc:
            logger.warning("Gemini growth feedback failed with %s: %s", model_name, exc)
            continue
        if text:
            _cache[cache_key] = text
            while len(_cache) > _CACHE_MAX:
                _cache.popitem(last=False)
            return text
    return None
