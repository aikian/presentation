"""[신규 추가] 발표 성장 분석(History 강화) 기능.

기능_추가_제안서.hwp "기능 2. 발표 성장 분석" 대응 모듈.
analysis_schema.py의 build_details()와 같은 방식으로, 여러 세션의
scores / summary / habits를 읽어 스키마 v0.1 규약을 따르는
"growth" JSON 조각을 만들어 낸다.

주의(스키마 노트 그대로 반영):
- weights_version이 다른 세션끼리는 총점(score_total)을 단순 비교하면
  불공정하다. 버전이 다르면 총점 비교는 생략하고 개별 지표만 비교한다.
- "비교 데이터 부족" 리스크 대응: 세션이 1개뿐이면 compare_with_previous는
  None으로 두고 trend만 채운다. (계획서: "발표 2회 이상부터 비교 기능 제공")
"""
from typing import Any

SCHEMA_VERSION = "0.1"


def _weights_version(row: dict[str, Any]) -> str | None:
    """analysis_results.details.scores.weights_version을 꺼낸다. 아직 없으면 None."""
    details = row.get("details") or {}
    scores = details.get("scores") or {}
    return scores.get("weights_version")


def _delta(current: float | int | None, previous: float | int | None) -> dict[str, Any] | None:
    """두 값의 변화량을 {current, previous, delta} 형태로 만든다. 값이 없으면 None."""
    if current is None or previous is None:
        return None
    return {
        "current": current,
        "previous": previous,
        "delta": round(current - previous, 2) if isinstance(current, float) else current - previous,
    }


def _trend_point(row: dict[str, Any]) -> dict[str, Any]:
    """이력 한 건을 그래프용 trend 포인트로 변환한다. (Chart.js에 그대로 투입 가능)"""
    details = row.get("details") or {}
    summary = details.get("summary") or {}
    return {
        "session_id": row.get("id"),
        "created_at": row.get("created_at"),
        "weights_version": _weights_version(row),
        "score_total": row.get("score_total"),
        "score_gaze": row.get("score_gaze"),
        "score_pose": row.get("score_pose"),
        "score_gesture": row.get("score_gesture"),
        "score_time": row.get("score_time"),
        # video_timeline/summary 담당자가 구현하면 자동으로 채워짐 (그 전엔 None)
        "gaze_away_ratio": summary.get("gaze_away_ratio", row.get("gaze_away_ratio")),
        "gesture_active_ratio": summary.get("gesture_active_ratio"),
    }


def _compare_with_previous(current_row: dict[str, Any], previous_row: dict[str, Any]) -> dict[str, Any]:
    same_weights = _weights_version(current_row) == _weights_version(previous_row)
    return {
        "comparable_by_total": same_weights,
        "score_total": _delta(current_row.get("score_total"), previous_row.get("score_total")) if same_weights else None,
        "score_gaze": _delta(current_row.get("score_gaze"), previous_row.get("score_gaze")),
        "score_pose": _delta(current_row.get("score_pose"), previous_row.get("score_pose")),
        "score_gesture": _delta(current_row.get("score_gesture"), previous_row.get("score_gesture")),
        "score_time": _delta(current_row.get("score_time"), previous_row.get("score_time")),
    }


def _growth_feedback(compare: dict[str, Any] | None) -> str | None:
    """간단한 규칙 기반 피드백. 3~4주차에 OpenAI API 호출로 교체 예정(계획서 목표 4)."""
    if compare is None:
        return None
    total = compare.get("score_total")
    if total is None:
        return "이전 발표와 채점 기준(weights_version)이 달라 총점 비교는 생략했습니다. 개별 지표를 확인해보세요."
    if total["delta"] > 0:
        return f"지난 발표보다 총점이 {total['delta']}점 상승했습니다. 성장하고 있어요!"
    if total["delta"] < 0:
        return f"지난 발표보다 총점이 {abs(total['delta'])}점 낮아졌습니다. 개선이 필요한 항목을 확인해보세요."
    return "지난 발표와 총점이 동일합니다."


def build_growth_report(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """세션 이력(최신순 정렬)을 받아 성장 리포트 JSON 조각을 만든다.

    Args:
        sessions: supabase `analysis_results` 조회 결과. created_at 내림차순
                  (가장 최근 발표가 sessions[0]).

    Returns:
        스키마 v0.1을 따르는 growth JSON 조각. 예)
        {
          "schema_version": "0.1",
          "growth": {
            "session_count": 3,
            "trend": [...],                 # 오래된 -> 최신 순 (그래프 x축 순서)
            "compare_with_previous": {...},  # 세션 1개뿐이면 None
            "feedback": "..."
          }
        }
    """
    if not sessions:
        return {
            "schema_version": SCHEMA_VERSION,
            "growth": {"session_count": 0, "trend": [], "compare_with_previous": None, "feedback": None},
        }

    trend = [_trend_point(row) for row in reversed(sessions)]  # 오래된 순으로 뒤집기 (그래프용)

    compare = None
    if len(sessions) >= 2:
        compare = _compare_with_previous(sessions[0], sessions[1])

    return {
        "schema_version": SCHEMA_VERSION,
        "growth": {
            "session_count": len(sessions),
            "trend": trend,
            "compare_with_previous": compare,
            "feedback": _growth_feedback(compare),
        },
    }
