# 자세

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

# 제스처

def extract_inactive_gesture_points(video_timeline: list[dict]) -> list[dict]:
    """
    video_timeline에서 제스처가 비활성 상태인 시점을 추출한다.

    gesture.active == False인 시점을 추출한다.
    """
    inactive_points = []

    for item in video_timeline:
        gesture = item.get("gesture")

        # 손 분석 결과가 없는 경우는 제스처 비활성으로 간주하지 않는다.
        if gesture is None:
            continue

        active = gesture.get("active")

        if active is False:
            inactive_points.append({
                "sec": item["sec"],
                "hands_visible": gesture.get("hands_visible"),
            })

    return inactive_points


def group_inactive_gesture_segments(inactive_points: list[dict], frame_interval_sec: float) -> list[dict]:
    """
    연속해서 나타난 제스처 비활성 시점을 하나의 구간으로 묶는다.

    frame_interval_sec 간격으로 이어지는 비활성 시점은
    동일한 구간으로 처리한다.
    """
    if not inactive_points:
        return []

    segments = []

    current_segment = {
        "start_sec": inactive_points[0]["sec"],
        "end_sec": inactive_points[0]["sec"],
    }

    for point in inactive_points[1:]:
        time_gap = point["sec"] - current_segment["end_sec"]

        if time_gap <= frame_interval_sec:
            current_segment["end_sec"] = point["sec"]
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
            }

    current_segment["duration_sec"] = round(
        current_segment["end_sec"]
        - current_segment["start_sec"]
        + frame_interval_sec,
        1,
    )
    segments.append(current_segment)

    return segments


def detect_gesture_inactivity_habit(segments: list[dict],persistent_threshold_sec: float) -> list[dict]:
    """
    제스처 비활성 구간 중 일정 시간 이상 지속된 구간을 추출한다.

    """
    persistent = []

    for segment in segments:
        if segment["duration_sec"] >= persistent_threshold_sec:
            persistent.append(segment)

    return persistent


def analyze_gesture_habits(video_timeline: list[dict],frame_interval_sec: float,persistent_threshold_sec: float) -> dict:
    """
    video_timeline을 기반으로 제스처 비활성 습관 탐지 전체 과정을 수행한다.

    """
    inactive_points = extract_inactive_gesture_points(video_timeline)

    segments = group_inactive_gesture_segments(
        inactive_points,
        frame_interval_sec,
    )

    persistent = detect_gesture_inactivity_habit(
        segments,
        persistent_threshold_sec,
    )

    return {
        "inactive_points": inactive_points,
        "segments": segments,
        "persistent": persistent,
    }


# 음성 - 군말

def extract_filler_points(filler_words: list[dict]) -> list[dict]:
    """
    filler_words에서 군말 발생 시점과 단어를 추출한다.
    """
    filler_points = []

    for item in filler_words:
        sec = item.get("sec")
        word = item.get("word")

        if sec is None or word is None:
            continue

        filler_points.append({
            "sec": float(sec),
            "word": word,
        })

    return filler_points


def count_fillers(filler_points: list[dict]) -> dict:
    """
    군말 발생 정보를 바탕으로 단어별 사용 횟수를 집계한다.
    """
    filler_counts = {}

    for point in filler_points:
        word = point.get("word")

        if word is None:
            continue

        filler_counts[word] = filler_counts.get(word, 0) + 1

    return filler_counts


def detect_repeated_filler_habits(filler_counts: dict, repeated_threshold_count: int) -> list[dict]:
    """
    단어별 군말 사용 횟수를 바탕으로 반복 군말 습관을 탐지한다.

    repeated_threshold_count:
        같은 군말이 이 횟수 이상 사용되면 반복형으로 판단한다.

    임계값은 현재 함수 내부에서 고정하지 않고 외부에서 전달받는다.
    """
    repeated = []

    for word, count in filler_counts.items():
        if count >= repeated_threshold_count:
            repeated.append({
                "word": word,
                "count": count,
            })

    return repeated


def analyze_filler_habits(filler_words: list[dict], repeated_threshold_count: int) -> dict:
    """
    filler_words를 기반으로 반복 군말 습관 탐지 전체 과정을 수행한다.
    """
    filler_points = extract_filler_points(filler_words)

    filler_counts = count_fillers(filler_points)

    repeated = detect_repeated_filler_habits(
        filler_counts,
        repeated_threshold_count,
    )

    return {"filler_points": filler_points, "filler_counts": filler_counts, "repeated": repeated}


# 음성 - 단조로움

def extract_monotone_points(audio_timeline: list[dict], monotone_threshold: float) -> list[dict]:
    """
    audio_timeline에서 이웃한 두 초의 피치 변화가
    monotone_threshold 미만인 시점을 추출한다.
    """
    monotone_points = []

    for prev, cur in zip(audio_timeline, audio_timeline[1:]):
        if cur["sec"] - prev["sec"] != 1.0:
            continue

        prev_pitch = prev.get("pitch_hz")
        cur_pitch = cur.get("pitch_hz")

        if not prev_pitch or not cur_pitch:
            continue

        change_ratio = abs(cur_pitch - prev_pitch) / prev_pitch

        if change_ratio < monotone_threshold:
            monotone_points.append({
                "sec": cur["sec"],
                "pitch_hz": cur_pitch,
                "change_ratio": round(change_ratio, 3),
            })

    return monotone_points


def group_monotone_segments(monotone_points: list[dict], frame_interval_sec: float) -> list[dict]:
    """
    연속해서 나타난 단조로운 피치 변화 시점을 하나의 구간으로 묶는다.

    각 monotone point는 이전 시점과 현재 시점 사이의 피치 변화가
    기준 미만임을 의미하므로, 구간 시작 시점에는 이전 간격을 포함한다.
    """
    if not monotone_points:
        return []

    segments = []

    current_segment = {
        "start_sec": monotone_points[0]["sec"] - frame_interval_sec,
        "end_sec": monotone_points[0]["sec"],
    }

    for point in monotone_points[1:]:
        time_gap = point["sec"] - current_segment["end_sec"]

        if time_gap <= frame_interval_sec:
            current_segment["end_sec"] = point["sec"]
        else:
            current_segment["duration_sec"] = round(
                current_segment["end_sec"]
                - current_segment["start_sec"],
                1,
            )
            segments.append(current_segment)

            current_segment = {
                "start_sec": point["sec"] - frame_interval_sec,
                "end_sec": point["sec"],
            }

    current_segment["duration_sec"] = round(
        current_segment["end_sec"]
        - current_segment["start_sec"],
        1,
    )
    segments.append(current_segment)

    return segments


def detect_monotone_habits(segments: list[dict], persistent_threshold_sec: float) -> list[dict]:
    """
    단조로운 피치 변화 구간 중 일정 시간 이상 지속된 구간을 추출한다.
    """
    persistent = []

    for segment in segments:
        if segment["duration_sec"] >= persistent_threshold_sec:
            persistent.append(segment)

    return persistent


def analyze_monotone_habits(audio_timeline: list[dict], monotone_threshold: float, persistent_threshold_sec: float, frame_interval_sec: float = 1.0) -> dict:
    """
    audio_timeline을 기반으로 단조로움 습관 탐지 전체 과정을 수행한다.
    """
    monotone_points = extract_monotone_points(
        audio_timeline,
        monotone_threshold,
    )

    segments = group_monotone_segments(
        monotone_points,
        frame_interval_sec,
    )

    persistent = detect_monotone_habits(
        segments,
        persistent_threshold_sec,
    )

    return {
        "monotone_points": monotone_points,
        "segments": segments,
        "persistent": persistent,
    }

