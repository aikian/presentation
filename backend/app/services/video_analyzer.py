import base64
import json
import logging
import math
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

import cv2
import mediapipe as mp
import numpy as np

from app.core.config import settings
from app.services.audio_analyzer import analyze_audio

mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands

logger = logging.getLogger(__name__)

# FaceMesh 랜드마크 인덱스
NOSE_TIP = 1
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 263

# EAR 계산용 눈 랜드마크 (p1=외각, p2~p3=위, p4=내각, p5~p6=아래)
LEFT_EYE_EAR = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_EAR = [33, 160, 158, 133, 153, 144]

# 입 랜드마크
UPPER_LIP = 13
LOWER_LIP = 14
MOUTH_LEFT = 61
MOUTH_RIGHT = 291

EAR_CLOSE_THRESHOLD = 0.2  # 이 값 미만이면 눈 감음
MAR_SPEAK_THRESHOLD = 0.25  # 이 값 이상이면 발화 중


def _frame_to_b64(frame: np.ndarray) -> str:
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return base64.b64encode(buf).decode()


def _landmark_pt(lm, idx, w, h):
    p = lm[idx]
    return np.array([p.x * w, p.y * h])


def _gaze_score(face_landmarks, w: int, h: int) -> float:
    """0=정면, 1=최대이탈. yaw(수평)+pitch(수직) 복합 추정."""
    lm = face_landmarks.landmark
    nose = lm[NOSE_TIP]
    left = lm[LEFT_EYE_OUTER]
    right = lm[RIGHT_EYE_OUTER]

    face_cx = (left.x + right.x) / 2
    face_cy = (left.y + right.y) / 2
    eye_dist = max(abs(right.x - left.x), 1e-6)

    yaw_dev = abs(nose.x - face_cx) / eye_dist
    pitch_dev = abs(nose.y - face_cy) / eye_dist * 0.6  # 수직 가중치 낮춤
    return min(max(yaw_dev, pitch_dev), 1.0)


def _ear(landmarks, eye_idxs, w: int, h: int) -> float:
    """Eye Aspect Ratio. 0=완전히 감음, ~0.3=정상."""
    pts = [_landmark_pt(landmarks, i, w, h) for i in eye_idxs]
    A = np.linalg.norm(pts[1] - pts[5])
    B = np.linalg.norm(pts[2] - pts[4])
    C = np.linalg.norm(pts[0] - pts[3])
    return float((A + B) / (2.0 * C)) if C > 1e-6 else 0.0


def _mar(landmarks, w: int, h: int) -> float:
    """Mouth Aspect Ratio. 값이 크면 입이 벌어짐(발화)."""
    lm = landmarks
    v = abs(lm[UPPER_LIP].y - lm[LOWER_LIP].y)
    h_dist = max(abs(lm[MOUTH_LEFT].x - lm[MOUTH_RIGHT].x), 1e-6)
    return v / h_dist


def _shoulder_tilt(pose_landmarks) -> float:
    return abs(_shoulder_tilt_signed(pose_landmarks))


def _shoulder_tilt_signed(pose_landmarks) -> float:
    l = pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER]
    r = pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER]

    angle = math.degrees(math.atan2(l.y - r.y, l.x - r.x))

    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180

    return angle


def _lean_direction(pose_landmarks, threshold_deg: float = 5.0) -> str:
    signed_tilt = _shoulder_tilt_signed(pose_landmarks)

    if abs(signed_tilt) < threshold_deg:
        return "none"

    return "left" if signed_tilt < 0 else "right"


def _extract_frames(video_path: Path):
    # OpenCV stderr 억제 (EBML/webm 파싱 경고)
    import os, sys
    devnull = open(os.devnull, 'w')
    old_stderr_fd = os.dup(2)
    os.dup2(devnull.fileno(), 2)
    try:
        cap = cv2.VideoCapture(str(video_path))
    finally:
        os.dup2(old_stderr_fd, 2)
        os.close(old_stderr_fd)
        devnull.close()

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps < 1 or fps > 120:
        fps = 30  # 브라우저 webm 녹화본의 FPS 파싱 실패 시 기본값

    interval = max(1, int(fps * settings.frame_interval_sec))
    frames = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % interval == 0:
            frames.append(frame)
        idx += 1
    cap.release()
    return frames


def analyze_video(video_path: Path, on_step=None) -> dict[str, Any]:
    def _step(n):
        if on_step:
            on_step(n)

    _step(1)
    frames = _extract_frames(video_path)
    if not frames:
        return {
            "gaze_away_ratio": None, "face_detected_ratio": 0.0,
            "shoulder_tilt_avg": None, "gesture_count": 0,
            "ear_blink_ratio": None, "silence_ratio": None,
            "gaze_timeline": [], "video_timeline": [], "problem_frames": [],
            "error": "영상에서 프레임을 추출할 수 없습니다.",
        }

    gaze_scores: list[float] = []
    gaze_timeline: list[dict] = []
    ear_values: list[float] = []
    mar_values: list[float] = []
    problem_gaze_frame: dict[str, Any] | None = None
    max_gaze_score = 0.0

    shoulder_tilts: list[float] = []
    problem_pose_frame: dict[str, Any] | None = None
    max_pose_tilt = 0.0
    gesture_count = 0
    prev_wrist_positions = []

    video_timeline = [{"sec": round(i * settings.frame_interval_sec, 1), "posture": None, "gesture": None} for i in range(len(frames))]

    # Step 2: 시선 + EAR + 입 분석 (FaceMesh)
    _step(2)
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    ) as face_mesh:
        for i, frame in enumerate(frames):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = face_mesh.process(rgb)
            if result.multi_face_landmarks:
                lm = result.multi_face_landmarks[0].landmark
                h, w = frame.shape[:2]

                score = _gaze_score(result.multi_face_landmarks[0], w, h)
                gaze_scores.append(score)
                gaze_timeline.append({"sec": round(i * settings.frame_interval_sec, 1), "score": round(score, 3)})

                if score > 0.35 and score > max_gaze_score:
                    max_gaze_score = score
                    problem_gaze_frame = {
                        "type": "gaze",
                        "label": "시선 이탈",
                        "sec": round(i * settings.frame_interval_sec, 1),
                        "score": round(score, 3),
                        "value": f"{score * 100:.0f}%",
                        "image": _frame_to_b64(frame),
                    }

                left_ear = _ear(lm, LEFT_EYE_EAR, w, h)
                right_ear = _ear(lm, RIGHT_EYE_EAR, w, h)
                ear_values.append((left_ear + right_ear) / 2)

                mar_values.append(_mar(lm, w, h))

    # Step 3: 자세 분석 (Pose)
    _step(3)
    with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
        for i, frame in enumerate(frames):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(rgb)
            if result.pose_landmarks:
                tilt = _shoulder_tilt(result.pose_landmarks)
                shoulder_tilts.append(tilt)

                lean_dir = _lean_direction(result.pose_landmarks)
                
                video_timeline[i]["posture"] = {
                    "shoulder_tilt_deg": round(tilt, 1),
                    "lean_dir": lean_dir,
                    "score": None,
                }
                if tilt > 10 and tilt > max_pose_tilt:
                    max_pose_tilt = tilt
                    problem_pose_frame = {
                        "type": "pose",
                        "label": "자세 기울어짐",
                        "sec": round(i * settings.frame_interval_sec, 1),
                        "score": round(tilt, 2),
                        "value": f"{tilt:.1f}도",
                        "image": _frame_to_b64(frame),
                    }

    # Step 4: 제스처 분석 (Hands)
    _step(4)
    with mp_hands.Hands(static_image_mode=True, max_num_hands=2, min_detection_confidence=0.5) as hands:
        for i, frame in enumerate(frames):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)
            hands_visible = bool(result.multi_hand_landmarks)
            video_timeline[i]["gesture"] = {
                "active": None,
                "hands_visible": hands_visible,
            }

            current_wrist_positions = []

            if result.multi_hand_landmarks:
                gesture_count += len(result.multi_hand_landmarks)

                for hand_landmarks in result.multi_hand_landmarks:
                    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                    current_wrist_positions.append(np.array([wrist.x, wrist.y]))

                if prev_wrist_positions:
                    remaining_prev = prev_wrist_positions.copy()
                    movements = []

                    for current in current_wrist_positions:
                        if not remaining_prev:
                            break

                        distances = [float(np.linalg.norm(current - prev)) for prev in remaining_prev]
                        min_idx = int(np.argmin(distances))
                        movements.append(distances[min_idx])
                        remaining_prev.pop(min_idx)

                    if movements:
                        movement_max = max(movements)
                        active = movement_max >= 0.10

                        video_timeline[i]["gesture"]["active"] = active


                prev_wrist_positions = current_wrist_positions
            else:
                prev_wrist_positions = []

    problem_frames = [frame for frame in (problem_gaze_frame, problem_pose_frame) if frame]
    gaze_away_ratio = float(np.mean([s > 0.35 for s in gaze_scores])) if gaze_scores else None
    face_detected_ratio = (len(gaze_scores) / len(frames)) if frames else 0.0
    shoulder_tilt_avg = float(np.mean(shoulder_tilts)) if shoulder_tilts else None

    # EAR 기반 눈 감음 비율
    ear_blink_ratio = float(np.mean([e < EAR_CLOSE_THRESHOLD for e in ear_values])) if ear_values else None

    # 입 움직임 기반 침묵 비율 (MAR이 낮으면 미발화)
    silence_ratio = float(np.mean([m < MAR_SPEAK_THRESHOLD for m in mar_values])) if mar_values else None


    return {
        "gaze_away_ratio": round(gaze_away_ratio, 3) if gaze_away_ratio is not None else None,
        "face_detected_ratio": round(face_detected_ratio, 3),
        "shoulder_tilt_avg": round(shoulder_tilt_avg, 2) if shoulder_tilt_avg is not None else None,
        "gesture_count": gesture_count,
        "ear_blink_ratio": round(ear_blink_ratio, 3) if ear_blink_ratio is not None else None,
        "silence_ratio": round(silence_ratio, 3) if silence_ratio is not None else None,
        "gaze_timeline": gaze_timeline,
        "video_timeline": video_timeline,
        "problem_frames": problem_frames,
    }



def _gemini_model_candidates() -> list[str]:
    configured = settings.gemini_model.strip().removeprefix("models/")
    candidates = [configured, "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]
    return list(dict.fromkeys(model for model in candidates if model))


def _build_coaching_prompt(metrics: dict) -> str:
    gaze_ratio = metrics.get("gaze_away_ratio")
    shoulder_tilt = metrics.get("shoulder_tilt_avg")
    blink_ratio = metrics.get("ear_blink_ratio")
    silence_ratio = metrics.get("silence_ratio")

    gaze_text = f"{gaze_ratio * 100:.1f}%" if gaze_ratio is not None else "분석 불가"
    pose_text = f"{shoulder_tilt:.1f}도" if shoulder_tilt is not None else "분석 불가"
    blink_text = f"{blink_ratio * 100:.1f}%" if blink_ratio is not None else "분석 불가"
    silence_text = f"{silence_ratio * 100:.1f}%" if silence_ratio is not None else "분석 불가"

    return f"""
당신은 발표 코치입니다. 다음 발표 분석 지표를 보고 한국어로 구체적인 개선 코칭을 작성하세요.

- 시선 이탈 비율: {gaze_text}
- 어깨 기울기 평균: {pose_text}
- 제스처 횟수: {metrics['gesture_count']}회
- 눈 감음 비율: {blink_text}
- 침묵 구간 비율: {silence_text}

반드시 아래 Markdown 템플릿의 제목과 순서를 그대로 유지하세요.
각 섹션은 짧고 실행 가능한 문장으로 작성하고, 코드블록이나 표는 사용하지 마세요.

## 한줄 요약
- 발표 전체를 한 문장으로 요약하세요.

## 시선
**진단:** 시선 이탈 수치를 바탕으로 현재 상태를 평가하세요.
**코칭:** 다음 연습에서 바로 시도할 구체 행동을 제안하세요.

## 자세
**진단:** 어깨 기울기 수치를 바탕으로 현재 상태를 평가하세요.
**코칭:** 상체 균형을 개선할 구체 행동을 제안하세요.

## 제스처
**진단:** 제스처 횟수를 바탕으로 현재 상태를 평가하세요.
**코칭:** 손동작을 더 효과적으로 쓰는 방법을 제안하세요.

## 집중도
**진단:** 눈 감음 비율을 바탕으로 청중 몰입감을 평가하세요.
**코칭:** 카메라와 청중을 더 안정적으로 마주 보는 방법을 제안하세요.

## 발화
**진단:** 침묵 구간 비율을 바탕으로 발표 흐름을 평가하세요.
**코칭:** 말의 흐름을 유지하는 연습 방법을 제안하세요.

## 다음 연습 우선순위
1. 가장 먼저 개선할 항목 하나를 제안하세요.
2. 그 다음으로 개선할 항목 하나를 제안하세요.
"""


def _generate_gemini_content(model_name: str, api_key: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": api_key,
        },
    )

    with urlrequest.urlopen(req, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))

    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "\n".join(part.get("text", "") for part in parts).strip()


def _gemini_coaching(metrics: dict, api_key: str) -> str:
    if not api_key:
        return _fallback_coaching(metrics)

    prompt = _build_coaching_prompt(metrics)
    for model_name in _gemini_model_candidates():
        try:
            text = _generate_gemini_content(model_name, api_key, prompt)
            if text:
                return text
        except (urlerror.HTTPError, urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger.warning("Gemini REST coaching failed with %s: %s", model_name, exc)

    return _fallback_coaching(metrics)


def _fallback_coaching(metrics: dict) -> str:
    gaze_ratio = metrics.get("gaze_away_ratio")
    shoulder_tilt = metrics.get("shoulder_tilt_avg")
    blink_ratio = metrics.get("ear_blink_ratio")
    silence_ratio = metrics.get("silence_ratio")

    ratio = gaze_ratio * 100 if gaze_ratio is not None else None
    tilt = shoulder_tilt if shoulder_tilt is not None else None
    gestures = metrics["gesture_count"]
    blink = blink_ratio * 100 if blink_ratio is not None else None
    silence = silence_ratio * 100 if silence_ratio is not None else None

    if ratio is None:
        gaze_diagnosis = "얼굴이 충분히 검출되지 않아 시선 분석이 어렵습니다."
        gaze_coaching = "얼굴 전체가 카메라 화면에 잘 보이도록 위치와 조명을 조정한 뒤 다시 분석해보세요."
    elif ratio > 30:
        gaze_diagnosis = f"발표 시간의 {ratio:.0f}% 동안 시선이 이탈해 청중과의 연결감이 약해질 수 있습니다."
        gaze_coaching = "핵심 문장을 말할 때마다 카메라를 2초 이상 바라보고, 슬라이드는 문장 사이에만 확인하세요."
    elif ratio > 15:
        gaze_diagnosis = f"시선 이탈이 {ratio:.0f}%로 약간 높아 중요한 메시지가 분산될 수 있습니다."
        gaze_coaching = "문단 시작과 결론 문장에서는 카메라를 먼저 본 뒤 슬라이드로 시선을 옮기는 리듬을 만드세요."
    else:
        gaze_diagnosis = f"시선 이탈이 {ratio:.0f}%로 안정적인 편입니다."
        gaze_coaching = "현재 리듬을 유지하되, 강조 문장에서는 카메라 응시 시간을 조금 더 길게 가져가세요."

    if tilt is None:
        pose_diagnosis = "자세가 충분히 검출되지 않아 어깨 기울기를 분석하기 어렵습니다."
        pose_coaching = "상체와 양쪽 어깨가 카메라 화면에 모두 보이도록 위치를 조정한 뒤 다시 분석해보세요."
    elif tilt > 15:
        pose_diagnosis = f"어깨 기울기가 평균 {tilt:.1f}도로 커서 화면에서 자세가 불안정해 보일 수 있습니다."
        pose_coaching = "발표 전 양발을 같은 간격으로 두고, 문단이 바뀔 때마다 어깨 높이를 한 번씩 점검하세요."
    elif tilt > 8:
        pose_diagnosis = f"어깨가 {tilt:.1f}도 기울어져 중간중간 상체 균형이 흐트러집니다."
        pose_coaching = "카메라 중앙에 코와 명치를 맞추고, 손 제스처 뒤에는 팔을 몸 옆으로 자연스럽게 되돌리세요."
    else:
        pose_diagnosis = f"어깨 균형이 {tilt:.1f}도로 잘 유지되고 있습니다."
        pose_coaching = "지금처럼 정면 자세를 유지하면서, 강조 구간에서는 상체를 살짝 앞으로 보내 전달력을 높이세요."

    if gestures < 5:
        gesture_diagnosis = "손 동작이 거의 없어 핵심 포인트의 강조가 약할 수 있습니다."
        gesture_coaching = "첫째, 둘째처럼 구조를 말할 때 손가락으로 번호를 보여주고, 결론에서는 양손을 가볍게 열어 강조하세요."
    elif gestures > 50:
        gesture_diagnosis = f"제스처가 {gestures}회로 많아 시선이 손동작에 분산될 수 있습니다."
        gesture_coaching = "문장마다 움직이기보다 핵심 단어 1개에만 손동작을 붙이고, 나머지 시간에는 손을 고정하세요."
    else:
        gesture_diagnosis = f"제스처 사용이 {gestures}회로 적절한 편입니다."
        gesture_coaching = "현재 빈도를 유지하면서 숫자, 방향, 크기 표현에 맞춰 제스처 종류를 분명히 나눠보세요."

    if blink is None:
        focus_diagnosis = "얼굴이 충분히 검출되지 않아 눈 감음 비율을 분석하기 어렵습니다."
        focus_coaching = "얼굴과 눈이 카메라 화면에 잘 보이도록 위치와 조명을 조정한 뒤 다시 분석해보세요."
    elif blink > 40:
        focus_diagnosis = f"눈 감음 비율이 {blink:.0f}%로 높아 피로하거나 자신감이 낮아 보일 수 있습니다."
        focus_coaching = "문장을 시작하기 전 숨을 짧게 들이마시고, 첫 단어를 말할 때 눈을 크게 뜨는 연습을 하세요."
    else:
        focus_diagnosis = f"눈 감음 비율이 {blink:.0f}%로 크게 문제되지 않습니다."
        focus_coaching = "발표 속도가 빨라질 때도 눈을 가늘게 뜨지 않도록 카메라 상단을 기준점으로 삼으세요."

    if silence is None:
        speech_diagnosis = "얼굴이 충분히 검출되지 않아 입 움직임 기반 침묵 비율을 분석하기 어렵습니다."
        speech_coaching = "얼굴과 입이 카메라 화면에 잘 보이도록 위치와 조명을 조정한 뒤 다시 분석해보세요."
    elif silence > 50:
        speech_diagnosis = f"침묵 구간이 {silence:.0f}%로 많아 발표 흐름이 자주 끊길 수 있습니다."
        speech_coaching = "슬라이드마다 첫 문장과 연결 문장을 미리 정해두고, 다음 장으로 넘어갈 때 짧은 브릿지 문장을 사용하세요."
    else:
        speech_diagnosis = f"침묵 구간이 {silence:.0f}%로 비교적 안정적입니다."
        speech_coaching = "지금 흐름을 유지하되, 중요한 설명 뒤에는 의도적인 1초 멈춤으로 강조를 만들어보세요."

    priorities = []
    if ratio is not None and ratio > 15:
        priorities.append("시선 이탈을 줄이기 위해 핵심 문장마다 카메라 응시를 고정하세요.")
    if tilt is not None and tilt > 8:
        priorities.append("어깨 균형을 맞추기 위해 발표 전 자세 기준점을 정하세요.")
    if gestures < 5 or gestures > 50:
        priorities.append("제스처 빈도를 조절해 강조 지점에만 손동작을 사용하세요.")
    if blink is not None and blink > 40:
        priorities.append("눈 감음 비율을 낮추기 위해 문장 시작 시 카메라를 또렷하게 바라보세요.")
    if silence is not None and silence > 50:
        priorities.append("침묵 구간을 줄이기 위해 슬라이드별 연결 문장을 준비하세요.")
    priorities = (priorities + [
        "발표 시작과 결론에서 카메라 응시를 의식적으로 유지하세요.",
        "다음 연습에서는 한 항목만 정해 녹화 후 바로 비교하세요.",
    ])[:2]

    gaze_summary = f"{ratio:.0f}%" if ratio is not None else "분석 불가"
    pose_summary = f"{tilt:.1f}도" if tilt is not None else "분석 불가"

    return "\n\n".join([
        f"## 한줄 요약\n- 시선 {gaze_summary}, 자세 {pose_summary}, 제스처 {gestures}회를 기준으로 다음 연습 포인트를 정리했습니다.",
        f"## 시선\n**진단:** {gaze_diagnosis}\n**코칭:** {gaze_coaching}",
        f"## 자세\n**진단:** {pose_diagnosis}\n**코칭:** {pose_coaching}",
        f"## 제스처\n**진단:** {gesture_diagnosis}\n**코칭:** {gesture_coaching}",
        f"## 집중도\n**진단:** {focus_diagnosis}\n**코칭:** {focus_coaching}",
        f"## 발화\n**진단:** {speech_diagnosis}\n**코칭:** {speech_coaching}",
        f"## 다음 연습 우선순위\n1. {priorities[0]}\n2. {priorities[1]}",
    ])

def _video_duration_sec(video_path: Path) -> float | None:
    """영상 길이(초). 스키마의 meta.duration_sec으로 나간다."""
    cap = cv2.VideoCapture(str(video_path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    finally:
        cap.release()

    if not fps or fps < 1 or fps > 120 or not frame_count or frame_count < 1:
        return None
    return round(frame_count / fps, 1)


def run_full_analysis(video_path: Path, api_key: str, on_step=None) -> dict[str, Any]:
    metrics = analyze_video(video_path, on_step)

    # 음성 분석. 실패해도 예외를 올리지 않으므로 영상 분석 결과는 그대로 살아남는다.
    if settings.enable_audio_analysis:
        metrics["audio_metrics"] = analyze_audio(video_path)
    else:
        metrics["audio_metrics"] = None

    metrics["duration_sec"] = _video_duration_sec(video_path)

    if on_step:
        on_step(5)
    coaching = _gemini_coaching(metrics, api_key)
    metrics["coaching"] = coaching
    return metrics
