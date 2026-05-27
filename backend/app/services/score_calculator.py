def _score(raw: float, good: float, bad: float) -> int:
    """DSD 3.7: score = clamp((1 - (raw-good)/(bad-good)) * 100, 0, 100)"""
    if abs(bad - good) < 1e-9:
        return 100
    return int(max(0, min(100, (1 - (raw - good) / (bad - good)) * 100)))


def calculate_scores(metrics: dict, goal_sec: float | None = None) -> dict:
    """분석 지표를 0~100 점수로 변환 (DSD 3.7 기준).

    가중치: 시선 30%, 자세 25%, 제스처 15%, 시간 30%
    """
    gaze = _score(metrics.get("gaze_away_ratio", 0), 0.0, 0.5)
    pose = _score(metrics.get("shoulder_tilt_avg", 0), 0.0, 20.0)

    g = metrics.get("gesture_count", 0)
    if g <= 15:
        gesture = _score(g, 15, 0)   # 0→0점, 15→100점
    else:
        gesture = _score(g, 15, 50)  # 15→100점, 50→0점
    gesture = max(0, min(100, gesture))

    if goal_sec and goal_sec > 0:
        elapsed = metrics.get("elapsed_sec") or goal_sec
        dev = abs(elapsed - goal_sec) / goal_sec
        time_score = _score(dev, 0.0, 0.3)
    else:
        time_score = 80  # 목표 시간 미설정 시 기본값

    total = int(gaze * 0.30 + pose * 0.25 + gesture * 0.15 + time_score * 0.30)

    return {
        "score_gaze": gaze,
        "score_pose": pose,
        "score_gesture": gesture,
        "score_time": time_score,
        "score_total": total,
    }
