from typing import Dict


def clamp(value: float, min_value: float = 0, max_value: float = 100) -> float:
    return max(min_value, min(value, max_value))


def linear_score(raw: float, good: float, bad: float) -> float:
    """
    DSD 3.7 점수 공식:
    score = clamp((1 - (raw - good) / (bad - good)) * 100, 0, 100)
    """

    if bad == good:
        return 100

    score = (1 - (raw - good) / (bad - good)) * 100
    return round(clamp(score), 1)


def gesture_score(gesture_count: int) -> float:
    #제스처는 너무 적어도 감점, 너무 많아도 감점. 최적값은 15회 기준.

    ideal = 15

    # 제스처가 적은 경우
    if gesture_count <= ideal:
        return linear_score(
            raw=ideal - gesture_count,
            good=0,
            bad=15
        )

    # 제스처가 많은 경우
    return linear_score(
        raw=gesture_count - ideal,
        good=0,
        bad=35
    )


def calculate_scores(
    analysis_result: Dict,
    goal_sec: int | None = None
) -> Dict:
    """
    입력:
      analyze_video() 결과 dict

    출력:
    {
        "gaze": 0~100,
        "pose": 0~100,
        "gesture": 0~100,
        "time": 0~100,
        "total": 0~100
    }
    """

    # -------------------------
    # 분석 결과 값 가져오기
    # -------------------------

    gaze_away_ratio = analysis_result.get("gaze_away_ratio", 0)
    shoulder_tilt_avg = analysis_result.get("shoulder_tilt_avg", 0)
    gesture_count = analysis_result.get("gesture_count", 0)
    elapsed_sec = analysis_result.get("elapsed_sec", 0)

    # -------------------------
    # 카테고리별 점수 계산
    # -------------------------

    # 시선 점수
    gaze = linear_score(
        raw=gaze_away_ratio,
        good=0.0,
        bad=0.5
    )

    # 자세 점수
    pose = linear_score(
        raw=shoulder_tilt_avg,
        good=0,
        bad=20
    )

    # 제스처 점수
    gesture = gesture_score(gesture_count)

    # 시간 점수
    if goal_sec and goal_sec > 0:
        time_diff_ratio = abs(elapsed_sec - goal_sec) / goal_sec

        time_score = linear_score(
            raw=time_diff_ratio,
            good=0.0,
            bad=0.3
        )
    else:
        time_score = 100

    # -------------------------
    # 최종 가중치 계산
    # -------------------------

    total = (
        gaze * 0.30 +
        pose * 0.25 +
        gesture * 0.15 +
        time_score * 0.30
    )

    return {
        "gaze": round(gaze, 1),
        "pose": round(pose, 1),
        "gesture": round(gesture, 1),
        "time": round(time_score, 1),
        "total": round(total, 1),
    }
