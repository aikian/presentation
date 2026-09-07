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











# 아래는 테스트용
test_points = [
    {"sec": 2.0, "tilt": 15.7, "direction": "right"},
    {"sec": 4.0, "tilt": 14.1, "direction": "right"},
    {"sec": 6.0, "tilt": 16.2, "direction": "right"},
    {"sec": 10.0, "tilt": 13.0, "direction": "left"},
    {"sec": 12.0, "tilt": 18.5, "direction": "left"},
]

print(group_posture_segments(test_points, 2.0))