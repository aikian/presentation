AHP_WEIGHTS = {
    "gaze": 0.3512,
    "posture": 0.1887,
    "gesture": 0.1089,
    "voice": 0.3512,
}


def _score(raw: float, good: float, bad: float) -> int:
    """DSD 3.7: score = clamp((1 - (raw-good)/(bad-good)) * 100, 0, 100)"""
    if abs(bad - good) < 1e-9:
        return 100
    return int(max(0, min(100, (1 - (raw - good) / (bad - good)) * 100)))


def _calculate_voice_score(audio_metrics: dict | None) -> int | None:
    """음성 분석 결과를 0~100점으로 변환한다.

    음성 세부 지표의 점수 기준과 내부 반영 비율이 확정되기 전까지
    None을 반환하여 종합점수 계산에서 제외한다.
    """
    if not audio_metrics or not audio_metrics.get("speech_available"):
        return None

    # TODO:
    # 말속도, 군말, 침묵, 단조로움의 점수 기준과
    # 음성 내부 반영 비율을 확정한 후 구현한다.
    return None


def _calculate_time_score(elapsed_sec: float | None, goal_sec: float | None) -> int | None:
    """목표 시간이 설정된 경우에만 시간 준수 점수를 계산한다."""
    if goal_sec is None or goal_sec <= 0:
        return None

    if elapsed_sec is None:
        return None

    deviation_ratio = abs(elapsed_sec - goal_sec) / goal_sec

    # TODO:
    # 목표 시간 대비 오차 30%를 0점으로 처리하는 기준은
    # 기존 구현값이므로 추후 기준을 검토한다.
    return _score(deviation_ratio, 0.0, 0.3)


def _calculate_total_score(scores: dict[str, int | None]) -> int | None:
    """분석 가능한 AHP 항목만 사용하여 종합점수를 계산한다."""
    available = [
        (score, AHP_WEIGHTS[name])
        for name, score in scores.items()
        if score is not None
    ]

    if not available:
        return None

    weighted_sum = sum(score * weight for score, weight in available)
    available_weight_sum = sum(weight for _, weight in available)

    return round(weighted_sum / available_weight_sum)


def calculate_scores(metrics: dict, goal_sec: float | None = None) -> dict:
    """분석 지표를 0~100점으로 변환한다.

    종합점수 가중치(AHP v2):
    시선 35.12%, 자세 18.87%, 제스처 10.89%, 음성 35.12%

    시간 점수는 목표 시간이 설정된 경우에만 별도로 계산하며,
    종합점수에는 포함하지 않는다.

    분석할 수 없거나 아직 구현되지 않은 항목은 None으로 두고,
    종합점수 계산 시 해당 항목을 제외한 뒤 가중치를 재정규화한다.
    """
    gaze_raw = metrics.get("gaze_away_ratio")

    # TODO:
    # 시선 이탈 비율 0%를 100점, 50%를 0점으로 처리하는 기준은
    # 기존 구현값이므로 문헌 및 실험 결과를 바탕으로 재검토한다.
    gaze = _score(gaze_raw, 0.0, 0.5) if gaze_raw is not None else None

    pose_raw = metrics.get("shoulder_tilt_avg")

    # TODO:
    # 어깨 기울기 0도를 100점, 20도를 0점으로 처리하는 기준은
    # 기존 구현값이므로 문헌 및 실험 결과를 바탕으로 재검토한다.
    pose = _score(pose_raw, 0.0, 20.0) if pose_raw is not None else None


    # TODO: D3
    # 현재 gesture_count는 프레임별 검출 손 개수의 누적값으로,
    # 영상 길이에 따라 증가하므로 점수 계산에 사용하지 않는다.
    # gesture_active_ratio와 비율 기반 점수 기준을 구현한 뒤 교체한다.
    gesture = None

    voice = _calculate_voice_score(metrics.get("audio_metrics"))

    time_score = _calculate_time_score(
        metrics.get("elapsed_sec"),
        goal_sec,
    )

    total = _calculate_total_score({
        "gaze": gaze,
        "posture": pose,
        "gesture": gesture,
        "voice": voice,
    })

    return {
        "score_gaze": gaze,
        "score_pose": pose,
        "score_gesture": gesture,
        "score_voice": voice,
        "score_time": time_score,
        "score_total": total,
    }