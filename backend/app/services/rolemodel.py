"""롤모델 벤치마킹: 사용자 발표를 명연사 기준선과 비교한다.

기준선은 `reference_speakers` 테이블의 연사들에게서 뽑는다.
비교 결과는 분석 결과 JSON의 `x_rolemodel` 필드에 담는다
(스키마 v0.1에 없는 실험 필드라 x_ 접두사. 회의에서 정식 승격 여부를 정한다).

지표를 고를 때는 "측정이 되는가"만 보지 않고 **"같은 사람에게 일관되게 나오는가"**를 본다.
같은 연사의 다른 강연에서 값이 크게 흔들리면 그날의 상태를 재는 것이지 발표 실력이 아니다.
김경일 연사의 강연이 두 편 있어서 이걸 대조군으로 쓴다.

연사 6명 7편 기준, 같은 연사의 변동이 전체 범위에서 차지하는 비율
(낮을수록 개인 특성을 잘 잡는다):

    단조로움 16% · 말속도 28% · 군말 37% · 피치편차 38% · 침묵 52%

**주의:** 대조군이 김경일 한 사람뿐이라 위 숫자는 잠정이다.
연사 4편이던 시점에는 피치편차가 100%로 나와 폐기했었는데,
연사를 늘리자 38%로 떨어져 판단이 뒤집혔다. 표본이 작으면 이런 일이 생긴다.
같은 연사의 강연이 둘 이상인 경우를 더 모으면 다시 계산해야 한다.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

# 비교에 쓰는 지표. (스키마 키, 사람이 읽는 이름, 낮을수록 좋은가)
# 같은 연사의 두 강연에서 값이 얼마나 흔들리는지 재보고 고른 것들이다.
#
# 세 번째 값이 None이면 "범위 안이 좋고 양쪽 다 벗어나면 문제"라는 뜻이다.
# 말 속도는 너무 빨라도 느려도 문제이고, 침묵도 너무 많으면 흐름이 끊기지만
# 너무 적으면 숨 돌릴 틈이 없어 듣기 힘들다.
COMPARED = [
    ("spm_avg", "말 속도", None),
    ("filler_per_min", "군말", True),         # 적을수록 좋다
    ("silence_ratio", "침묵 비율", None),
    ("monotone_ratio", "억양 단조로움", True),  # 억양 변화가 많을수록 좋다
    ("pitch_std", "억양 폭", None),            # 너무 밋밋해도, 너무 출렁여도 듣기 불편하다
]

# 기준선을 만들 만큼 연사가 모였는지 판단하는 최소 개수.
MIN_REFERENCES = 2


def build_baseline(references: list[dict[str, Any]]) -> dict[str, Any] | None:
    """연사들의 audio_summary에서 지표별 기준 범위를 만든다.

    평균 하나로 줄이지 않고 최소~최대 범위를 쓴다.
    연사마다 스타일이 달라서 평균은 아무도 아닌 값이 되기 쉽다.
    """
    summaries = [r.get("audio_summary") or {} for r in references]
    if len(summaries) < MIN_REFERENCES:
        return None

    baseline: dict[str, Any] = {}
    for key, _, _ in COMPARED:
        values = [s[key] for s in summaries if s.get(key) is not None]
        if len(values) < MIN_REFERENCES:
            continue
        baseline[key] = {
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "n": len(values),
        }

    return baseline or None


def _verdict(value: float, lo: float, hi: float, lower_is_better: bool | None) -> tuple[str, bool]:
    """(위치, 고쳐야 하는가). 위치와 좋고 나쁨은 다르다.

    군말은 명연사보다 적으면 오히려 좋다. 위치만 알려주면
    "범위보다 낮음"이 문제처럼 읽히므로 concern을 따로 둔다.
    """
    if lo <= value <= hi:
        return "within", False
    position = "below" if value < lo else "above"
    if lower_is_better is None:
        # 범위를 벗어난 것 자체가 문제인 지표 (말 속도)
        return position, True
    better_side = "below" if lower_is_better else "above"
    return position, position != better_side


def compare(user_summary: dict[str, Any] | None,
            references: list[dict[str, Any]]) -> dict[str, Any] | None:
    """사용자의 audio.summary를 롤모델 기준선과 비교한다.

    비교할 수 없으면 None. 읽는 쪽은 null 방어가 필요하다.
    """
    if not user_summary:
        return None

    baseline = build_baseline(references)
    if not baseline:
        logger.info("롤모델 기준선을 만들 연사가 부족합니다 (필요 %d명)", MIN_REFERENCES)
        return None

    metrics = []
    for key, label, lower_is_better in COMPARED:
        band = baseline.get(key)
        value = user_summary.get(key)
        if band is None or value is None:
            continue

        position, concern = _verdict(value, band["min"], band["max"], lower_is_better)
        metrics.append({
            "key": key,
            "label": label,
            "value": round(value, 3),
            "reference_min": band["min"],
            "reference_max": band["max"],
            "position": position,
            "concern": concern,
        })

    if not metrics:
        return None

    return {
        "reference_count": len(references),
        "reference_names": sorted({r["name"] for r in references if r.get("name")}),
        "metrics": metrics,
    }


def coaching_lines(comparison: dict[str, Any] | None) -> list[str]:
    """비교 결과를 코칭 프롬프트에 넣을 문장으로 만든다."""
    if not comparison:
        return []

    names = ", ".join(comparison["reference_names"])
    lines = [
        f"[롤모델 비교] 기준: {names} 등 발표 {comparison['reference_count']}편의 실측 범위",
    ]

    for m in comparison["metrics"]:
        lo, hi = m["reference_min"], m["reference_max"]
        if m["position"] == "within":
            state = "범위 안"
        elif m["concern"]:
            state = "많음, 개선 필요" if m["position"] == "above" else "적음, 개선 필요"
        else:
            state = "명연사보다 좋음"
        lines.append(f"- {m['label']}: {m['value']} (명연사 {lo}~{hi}) → {state}")

    lines.append("위 범위는 명연사 실측값이므로, 벗어난 항목만 짚고 범위 안인 항목은 칭찬하세요.")
    return lines
