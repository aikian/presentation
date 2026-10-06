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


# ---------------------------------------------------------------------------
# 음성 점수
# ---------------------------------------------------------------------------

# 점수 기준선. 2026-08-12에 측정한 연사 6명 7편(세바시)의 실측 범위를 상수로 박아둔다.
#
# **DB(reference_speakers)를 읽지 않고 상수를 쓰는 이유:**
# 연사를 더 추가하면 기준선이 넓어져 같은 발표의 점수가 달라진다.
# 그러면 지난주 70점과 이번주 70점이 다른 뜻이 되어 성장 그래프가 무의미해진다.
# 가중치를 weights_version으로 고정하는 것과 같은 이유다.
# 기준선을 바꿀 때는 회의에서 정하고 VOICE_BASELINE_VERSION을 올린다.
#
# **지표별 비율(weight)을 이렇게 둔 근거:**
# 같은 연사의 다른 강연에서 값이 얼마나 흔들리는지(개인 내 변동 / 전체 범위)를 재서,
# 흔들림이 적은 지표에 더 무게를 뒀다. 흔들리는 지표로 점수를 매기면 그날의 컨디션을
# 실력으로 오해하게 된다.
#
#     단조로움 16% · 말속도 28% · 군말 37% · 침묵 52%
#
# 이 순서대로 30 / 30 / 25 / 15를 배정했다.
# 억양 폭(pitch_std)은 범위 비교에는 쓰지만 점수에서는 뺐다. 신뢰도가 38%로 낮고,
# 성별과 타고난 음역에 크게 좌우되어 발표 실력으로 보기 어렵다.
# 억양 변화는 monotone_ratio가 이미 대표한다.
#
# **주의:** 대조군이 김경일 연사 한 사람뿐이라 위 신뢰도 숫자는 잠정이다.
VOICE_BASELINE_VERSION = "ref-7-2026-08"

VOICE_BASELINE = {
    # 키: (사람이 읽는 이름, 하한, 상한, 가중치, 낮을수록 좋은가)
    "spm_avg": ("말 속도", 319.7, 411.7, 0.30, None),
    "monotone_ratio": ("억양 단조로움", 0.137, 0.245, 0.30, True),
    "filler_per_min": ("군말", 1.49, 2.85, 0.25, True),
    "silence_ratio": ("침묵 비율", 0.135, 0.250, 0.15, None),
}


def _metric_score(value: float, lo: float, hi: float, lower_is_better: bool | None) -> int:
    """지표 하나를 0~100점으로 만든다.

    명연사 범위 안이면 100점이고, 벗어나면 벗어난 거리에 비례해 깎는다.
    **범위 폭만큼 벗어났을 때 0점**이 되도록 잡았다. 조금 벗어난 것과 많이 벗어난 것을
    같게 취급하면 "개선 필요"라는 판정이 설득력을 잃는다.

    예) 말 속도 범위는 319.7~411.7(폭 92)이다.
        312음절이면 7.7 모자라므로 100 - 100 x (7.7 / 92) = 92점.
        250음절이면 69.7 모자라므로 24점.

    군말과 단조로움은 범위보다 낮으면 오히려 좋으므로 100점을 준다.
    말 속도와 침묵은 너무 적어도 문제라서 양쪽 다 깎는다
    (침묵이 없으면 듣는 사람이 숨 돌릴 틈이 없다).
    """
    width = hi - lo
    if width <= 0:
        return 100

    if lo <= value <= hi:
        return 100

    if value < lo:
        if lower_is_better is True:
            return 100
        distance = lo - value
    else:
        if lower_is_better is False:
            return 100
        distance = value - hi

    return int(max(0, min(100, round(100 - 100 * distance / width))))


def voice_score_detail(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    """음성 요약 지표를 점수와 판정 근거로 바꾼다.

    점수 하나만 돌려주지 않고 지표별 점수와 판정 이유를 함께 담는다.
    "왜 이 점수인가"를 화면과 코칭에서 그대로 보여줄 수 있어야 한다.

    측정되지 않은 지표(None)는 빼고 남은 가중치로 다시 나눈다.
    하나도 못 재면 None이다(0점이 아니다. 0점은 "말을 못했다"는 뜻이 된다).
    """
    if not summary:
        return None

    metrics = []
    for key, (label, lo, hi, weight, lower_is_better) in VOICE_BASELINE.items():
        value = summary.get(key)
        if value is None:
            continue

        value = float(value)
        score = _metric_score(value, lo, hi, lower_is_better)

        if lo <= value <= hi:
            position, verdict = "within", "명연사 범위 안"
        elif value < lo:
            position = "below"
            verdict = "명연사보다 좋음" if lower_is_better is True else "기준보다 낮음"
        else:
            position = "above"
            verdict = "기준보다 높음" if lower_is_better is not False else "명연사보다 좋음"

        metrics.append({
            "key": key,
            "label": label,
            "value": round(value, 3),
            "reference_min": lo,
            "reference_max": hi,
            "position": position,
            "score": score,
            "weight": weight,
            "verdict": verdict,
            # 점수를 깎은 항목만 개선 대상으로 본다. 범위를 벗어났어도
            # 좋은 쪽으로 벗어난 것은 고칠 게 없다.
            "concern": score < 100,
        })

    if not metrics:
        return None

    weight_sum = sum(m["weight"] for m in metrics)
    total = round(sum(m["score"] * m["weight"] for m in metrics) / weight_sum)

    # 개선 우선순위: 가중치까지 반영해 총점을 가장 많이 깎은 항목이 먼저다.
    # 점수만 보면 가중치 15%인 침묵이 30%인 말 속도보다 앞설 수 있다.
    concerns = sorted(
        (m for m in metrics if m["concern"]),
        key=lambda m: (100 - m["score"]) * m["weight"],
        reverse=True,
    )

    return {
        "baseline_version": VOICE_BASELINE_VERSION,
        "score": total,
        "metrics": metrics,
        "priority": [m["key"] for m in concerns],
        "measured_weight": round(weight_sum, 2),
    }


def voice_score(summary: dict[str, Any] | None) -> int | None:
    """음성 종합점수만 꺼낸다. 근거까지 필요하면 voice_score_detail을 쓴다."""
    detail = voice_score_detail(summary)
    return detail["score"] if detail else None
