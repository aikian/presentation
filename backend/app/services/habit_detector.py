def extract_problem_posture_points(video_timeline: list[dict]) -> list[dict]:
    """
    video_timeline에서 문제 자세 시점을 추출한다.

    기존 프로토타입의 problem_pose_frame 추출 기준(shoulder_tilt_deg > 10)을
    재사용한다. 해당 10도 기준의 근거는 현재 확인되지 않았으므로,
    추후 재확인한다.
    """

    problem_points = []

    for item in video_timeline:
        posture = item.get("posture")

        if posture is None:
            continue

        tilt = posture.get("shoulder_tilt_deg")

        if tilt is not None and tilt > 10:
            problem_points.append({
                "sec": item["sec"],
                "tilt": tilt,
                "direction": posture.get("lean_dir"),
            })

    return problem_points


def group_posture_segments(problem_points: list[dict], frame_interval_sec: float) -> list[dict]:
    """
    연속해서 나타난 문제 자세 시점을 하나의 구간으로 묶는다.

    같은 방향의 문제 자세가 frame_interval_sec 간격으로 이어지는 경우
    동일한 구간으로 처리한다.
    """
    if not problem_points:
        return []

    segments = []

    current_segment = {
        "start_sec": problem_points[0]["sec"],
        "end_sec": problem_points[0]["sec"],
        "direction": problem_points[0]["direction"],
        "max_tilt": problem_points[0]["tilt"],
    }

    for point in problem_points[1:]:
        time_gap = point["sec"] - current_segment["end_sec"]
        same_direction = point["direction"] == current_segment["direction"]

        if time_gap <= frame_interval_sec and same_direction:
            current_segment["end_sec"] = point["sec"]
            current_segment["max_tilt"] = max(
                current_segment["max_tilt"],
                point["tilt"],
            )
        else:
            current_segment["duration_sec"] = round(
                current_segment["end_sec"]
                - current_segment["start_sec"]
                + frame_interval_sec,
                1,
            )
            segments.append(current_segment)

            current_segment = {
                "start_sec": point["sec"],
                "end_sec": point["sec"],
                "direction": point["direction"],
                "max_tilt": point["tilt"],
            }

    current_segment["duration_sec"] = round(
        current_segment["end_sec"]
        - current_segment["start_sec"]
        + frame_interval_sec,
        1,
    )
    segments.append(current_segment)

    return segments


def detect_posture_habits(segments: list[dict], persistent_threshold_sec: float, repeated_threshold_count: int) -> dict:
    """
    문제 자세 구간을 바탕으로 지속형/반복형 자세 습관을 탐지한다.

    persistent_threshold_sec:
        한 문제 자세 구간이 이 시간 이상 지속되면 지속형으로 판단한다.

    repeated_threshold_count:
        같은 방향의 문제 자세 구간이 이 횟수 이상 나타나면 반복형으로 판단한다.

    임계값은 현재 함수 내부에서 고정하지 않고 외부에서 전달받는다.
    """

    persistent = []
    repeated = []

    # 1. 지속형 탐지
    for segment in segments:
        if segment["duration_sec"] >= persistent_threshold_sec:
            persistent.append(segment)

    # 2. 방향별 반복 횟수 계산
    direction_counts = {}

    for segment in segments:
        direction = segment.get("direction")

        if direction in ("left", "right"):
            direction_counts[direction] = direction_counts.get(direction, 0) + 1

    # 3. 반복형 탐지
    for direction, count in direction_counts.items():
        if count >= repeated_threshold_count:
            repeated.append({
                "direction": direction,
                "count": count,
            })

    return {
        "persistent": persistent,
        "repeated": repeated,
    }


def analyze_posture_habits(video_timeline: list[dict], frame_interval_sec: float, persistent_threshold_sec: float, repeated_threshold_count: int) -> dict:
    """
    video_timeline을 기반으로 자세 습관 탐지 전체 과정을 수행한다.
    """

    problem_points = extract_problem_posture_points(video_timeline)

    segments = group_posture_segments(
        problem_points,
        frame_interval_sec,
    )

    habits = detect_posture_habits(
        segments,
        persistent_threshold_sec,
        repeated_threshold_count,
    )

    return {
        "problem_points": problem_points,
        "segments": segments,
        "habits": habits,
    }

