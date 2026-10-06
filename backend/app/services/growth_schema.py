"""발표 성장 분석(History 강화) - growth JSON 조각 빌더.

기능_추가_제안서.hwp "기능 2. 발표 성장 분석" 대응 모듈.
여러 세션의 scores / summary / habits / audio를 읽어 스키마 v0.1 규약을 따르는
"growth" JSON 조각을 만든다.

주의(스키마 노트 그대로 반영):
- weights_version이 다른 세션끼리는 총점(score_total)을 단순 비교하면 불공정하다.
  버전이 다르면 총점 비교는 생략하고 개별 지표만 비교한다.
- "비교 데이터 부족" 리스크 대응: 세션이 1개뿐이면 compare_with_previous는 None,
  trend만 채운다. (계획서: "발표 2회 이상부터 비교 기능 제공")

[이번 수정]
- 제안서 시나리오 4번의 "점수, 시선 유지율, 자세, 제스처, 발표 속도" 변화를 모두 비교하도록
  compare_with_previous.metrics(리스트)를 추가했다. (기존 score_* 키는 그대로 유지)
- 지표마다 improved / declined / same / changed 판정을 붙여 프론트 표시와 AI 프롬프트에 함께 쓴다.
- 규칙 기반 피드백을 AI 피드백과 같은 3단 형식으로 바꿨다. (AI 호출 실패 시 대체용)
"""
from typing import Any

SCHEMA_VERSION = "0.1"

# (key, 라벨, 단위, 좋은 방향, 표시 배율)
#  - better: "higher"=클수록 좋음 / "lower"=작을수록 좋음 / None=좋고 나쁨을 단정할 수 없음(변화만 표시)
#  - scale : 비율(0~1) 지표를 %로 보여주기 위한 배율
_METRICS: list[tuple[str, str, str, str | None, float]] = [
    ("score_total", "총점", "점", "higher", 1),
    ("score_gaze", "시선 점수", "점", "higher", 1),
    ("score_pose", "자세 점수", "점", "higher", 1),
    ("score_gesture", "제스처 점수", "점", "higher", 1),
    ("score_time", "시간 점수", "점", "higher", 1),
    ("gaze_away_ratio", "시선 이탈률", "%", "lower", 100),
    ("shoulder_tilt_avg", "어깨 기울기", "도", "lower", 1),
    ("gesture_count", "제스처 횟수", "회", None, 1),
    ("spm_avg", "발표 속도", "SPM", None, 1),
    ("filler_count", "필러워드", "회", "lower", 1),
]

VERDICT_LABEL = {"improved": "개선", "declined": "하락", "same": "변화 없음", "changed": "변화"}


def _first(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _weights_version(row: dict[str, Any]) -> str | None:
    """analysis_results.details.scores.weights_version을 꺼낸다. 아직 없으면 None."""
    details = row.get("details") or {}
    scores = details.get("scores") or {}
    return scores.get("weights_version")


def _metric_values(row: dict[str, Any]) -> dict[str, Any]:
    """이력 한 건에서 비교 대상 지표를 평평한 dict로 뽑는다. 없는 값은 None."""
    details = row.get("details") or {}
    summary = details.get("summary") or {}
    audio_summary = (details.get("audio") or {}).get("summary") or {}
    return {
        "score_total": row.get("score_total"),
        "score_gaze": row.get("score_gaze"),
        "score_pose": row.get("score_pose"),
        "score_gesture": row.get("score_gesture"),
        "score_time": row.get("score_time"),
        "gaze_away_ratio": _first(summary.get("gaze_away_ratio"), row.get("gaze_away_ratio")),
        "shoulder_tilt_avg": _first(summary.get("posture_tilt_avg_deg"), row.get("shoulder_tilt_avg")),
        "gesture_count": row.get("gesture_count"),
        "spm_avg": audio_summary.get("spm_avg"),
        "filler_count": audio_summary.get("filler_count"),
    }


def _delta(current: float | int | None, previous: float | int | None) -> dict[str, Any] | None:
    """두 값의 변화량을 {current, previous, delta} 형태로 만든다. 값이 없으면 None."""
    if current is None or previous is None:
        return None
    return {"current": current, "previous": previous, "delta": round(current - previous, 2)}


def _trend_point(row: dict[str, Any]) -> dict[str, Any]:
    """이력 한 건을 그래프용 trend 포인트로 변환한다. (차트 라이브러리에 그대로 투입 가능)"""
    details = row.get("details") or {}
    summary = details.get("summary") or {}
    return {
        "session_id": row.get("id"),
        "created_at": row.get("created_at"),
        "weights_version": _weights_version(row),
        **_metric_values(row),
        # video_timeline/summary 담당자가 구현하면 자동으로 채워짐 (그 전엔 None)
        "gesture_active_ratio": summary.get("gesture_active_ratio"),
    }


def _verdict(delta: float, better: str | None) -> str:
    if delta == 0:
        return "same"
    if better == "higher":
        return "improved" if delta > 0 else "declined"
    if better == "lower":
        return "improved" if delta < 0 else "declined"
    return "changed"


def _compare_with_previous(current_row: dict[str, Any], previous_row: dict[str, Any]) -> dict[str, Any]:
    same_weights = _weights_version(current_row) == _weights_version(previous_row)
    current_values = _metric_values(current_row)
    previous_values = _metric_values(previous_row)

    metrics: list[dict[str, Any]] = []
    for key, label, unit, better, scale in _METRICS:
        if key == "score_total" and not same_weights:
            continue  # 채점 기준이 다르면 총점 비교는 하지 않는다.
        current, previous = current_values.get(key), previous_values.get(key)
        if current is None or previous is None:
            continue
        current, previous = round(current * scale, 1), round(previous * scale, 1)
        delta = round(current - previous, 1)
        metrics.append(
            {
                "key": key,
                "label": label,
                "unit": unit,
                "current": current,
                "previous": previous,
                "delta": delta,
                "better": better,
                "verdict": _verdict(delta, better),
            }
        )

    return {
        "comparable_by_total": same_weights,
        "score_total": _delta(current_row.get("score_total"), previous_row.get("score_total")) if same_weights else None,
        "score_gaze": _delta(current_row.get("score_gaze"), previous_row.get("score_gaze")),
        "score_pose": _delta(current_row.get("score_pose"), previous_row.get("score_pose")),
        "score_gesture": _delta(current_row.get("score_gesture"), previous_row.get("score_gesture")),
        "score_time": _delta(current_row.get("score_time"), previous_row.get("score_time")),
        "metrics": metrics,
        "improved": [m["label"] for m in metrics if m["verdict"] == "improved"],
        "declined": [m["label"] for m in metrics if m["verdict"] == "declined"],
    }


def _line(metric: dict[str, Any]) -> str:
    unit = metric["unit"]
    return f"{metric['label']} {metric['previous']}{unit} → {metric['current']}{unit} ({metric['delta']:+.1f}{unit})"


def rule_based_feedback(compare: dict[str, Any] | None) -> str | None:
    """AI(Gemini) 호출이 실패하거나 꺼져 있을 때 쓰는 규칙 기반 피드백.

    AI 피드백과 같은 3단 형식(## 성장한 부분 / ## 개선이 필요한 부분 / ## 다음 연습 제안)을 쓴다.
    """
    if compare is None:
        return None

    metrics = compare.get("metrics") or []
    improved = [m for m in metrics if m["verdict"] == "improved"]
    declined = [m for m in metrics if m["verdict"] == "declined"]

    grew = [f"- {_line(m)}" for m in improved[:3]] or ["- 뚜렷하게 좋아진 항목은 아직 없어요. 다음 발표에서 한 가지에 집중해 보세요."]
    todo = [f"- {_line(m)}" for m in declined[:3]] or ["- 낮아진 항목이 없습니다. 지금 흐름을 유지하세요!"]

    if declined:
        worst = max(declined, key=lambda m: abs(m["delta"]))
        next_step = f"- 다음 연습에서는 '{worst['label']}'을(를) 먼저 챙겨 보세요."
    else:
        next_step = "- 다음 연습에서는 가장 점수가 낮은 항목 하나를 정해 녹화 후 바로 비교해 보세요."

    lines = ["## 성장한 부분", *grew, "", "## 개선이 필요한 부분", *todo, "", "## 다음 연습 제안", next_step]
    if not compare.get("comparable_by_total"):
        lines += ["", "※ 이전 발표와 채점 기준(weights_version)이 달라 총점 비교는 생략하고 개별 지표만 비교했습니다."]
    return "\n".join(lines)


def build_growth_report(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """세션 이력(최신순 정렬)을 받아 성장 리포트 JSON 조각을 만든다.

    Args:
        sessions: supabase `analysis_results` 조회 결과. created_at 내림차순
                  (가장 최근 발표가 sessions[0]).

    Returns:
        {
          "schema_version": "0.1",
          "growth": {
            "session_count": 3,
            "trend": [...],                  # 오래된 -> 최신 순 (그래프 x축 순서)
            "compare_with_previous": {...},  # 세션 1개뿐이면 None
            "feedback": "...",
            "feedback_source": "rule"        # history 라우터에서 AI 성공 시 "ai"로 바뀐다
          }
        }
    """
    if not sessions:
        return {
            "schema_version": SCHEMA_VERSION,
            "growth": {
                "session_count": 0,
                "trend": [],
                "compare_with_previous": None,
                "feedback": None,
                "feedback_source": None,
            },
        }

    trend = [_trend_point(row) for row in reversed(sessions)]  # 오래된 순으로 뒤집기 (그래프용)

    compare = None
    if len(sessions) >= 2:
        compare = _compare_with_previous(sessions[0], sessions[1])

    feedback = rule_based_feedback(compare)
    return {
        "schema_version": SCHEMA_VERSION,
        "growth": {
            "session_count": len(sessions),
            "trend": trend,
            "compare_with_previous": compare,
            "feedback": feedback,
            "feedback_source": "rule" if feedback else None,
        },
    }
