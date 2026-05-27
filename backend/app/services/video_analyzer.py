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
    l = pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER]
    r = pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    return abs(math.degrees(math.atan2(l.y - r.y, l.x - r.x)))


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
            "gaze_away_ratio": 0.0, "shoulder_tilt_avg": 0.0, "gesture_count": 0,
            "ear_blink_ratio": 0.0, "silence_ratio": 0.0,
            "gaze_timeline": [], "problem_frames": [],
            "error": "영상에서 프레임을 추출할 수 없습니다.",
        }

    gaze_scores: list[float] = []
    gaze_timeline: list[dict] = []
    ear_values: list[float] = []
    mar_values: list[float] = []
    problem_gaze_frames: list[np.ndarray] = []

    shoulder_tilts: list[float] = []
    problem_pose_frames: list[np.ndarray] = []
    gesture_count = 0

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

                if score > 0.35 and len(problem_gaze_frames) < 3:
                    problem_gaze_frames.append(frame)

                left_ear = _ear(lm, LEFT_EYE_EAR, w, h)
                right_ear = _ear(lm, RIGHT_EYE_EAR, w, h)
                ear_values.append((left_ear + right_ear) / 2)

                mar_values.append(_mar(lm, w, h))

    # Step 3: 자세 분석 (Pose)
    _step(3)
    with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(rgb)
            if result.pose_landmarks:
                tilt = _shoulder_tilt(result.pose_landmarks)
                shoulder_tilts.append(tilt)
                if tilt > 10 and len(problem_pose_frames) < 2:
                    problem_pose_frames.append(frame)

    # Step 4: 제스처 분석 (Hands)
    _step(4)
    with mp_hands.Hands(static_image_mode=True, max_num_hands=2, min_detection_confidence=0.5) as hands:
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)
            if result.multi_hand_landmarks:
                gesture_count += len(result.multi_hand_landmarks)

    problem_frames = [_frame_to_b64(f) for f in problem_gaze_frames + problem_pose_frames]
    gaze_away_ratio = float(np.mean([s > 0.35 for s in gaze_scores])) if gaze_scores else 0.0
    shoulder_tilt_avg = float(np.mean(shoulder_tilts)) if shoulder_tilts else 0.0

    # EAR 기반 눈 감음 비율
    ear_blink_ratio = float(np.mean([e < EAR_CLOSE_THRESHOLD for e in ear_values])) if ear_values else 0.0

    # 입 움직임 기반 침묵 비율 (MAR이 낮으면 미발화)
    silence_ratio = float(np.mean([m < MAR_SPEAK_THRESHOLD for m in mar_values])) if mar_values else 0.0

    return {
        "gaze_away_ratio": round(gaze_away_ratio, 3),
        "shoulder_tilt_avg": round(shoulder_tilt_avg, 2),
        "gesture_count": gesture_count,
        "ear_blink_ratio": round(ear_blink_ratio, 3),
        "silence_ratio": round(silence_ratio, 3),
        "gaze_timeline": gaze_timeline,
        "problem_frames": problem_frames,
    }



def _gemini_model_candidates() -> list[str]:
    configured = settings.gemini_model.strip().removeprefix("models/")
    candidates = [configured, "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]
    return list(dict.fromkeys(model for model in candidates if model))


def _build_coaching_prompt(metrics: dict) -> str:
    return f"""
당신은 발표 코치입니다. 다음 발표 분석 지표를 보고 한국어로 구체적인 개선 코칭을 작성하세요.

- 시선 이탈 비율: {metrics['gaze_away_ratio'] * 100:.1f}%
- 어깨 기울기 평균: {metrics['shoulder_tilt_avg']:.1f}도
- 제스처 횟수: {metrics['gesture_count']}회
- 눈 감음 비율: {metrics['ear_blink_ratio'] * 100:.1f}%
- 침묵 구간 비율: {metrics['silence_ratio'] * 100:.1f}%

각 항목별로 현재 상태를 평가하고, 바로 실천할 수 있는 개선 방법을 1~2문장씩 제시하세요.
마지막에는 발표자가 다음 연습에서 집중할 우선순위 2개를 제안하세요.
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
    lines = []
    ratio = metrics["gaze_away_ratio"] * 100
    tilt = metrics["shoulder_tilt_avg"]
    gestures = metrics["gesture_count"]
    blink = metrics.get("ear_blink_ratio", 0) * 100
    silence = metrics.get("silence_ratio", 0) * 100

    if ratio > 30:
        lines.append(f"시선: 발표 시간의 {ratio:.0f}% 동안 시선이 이탈했습니다. 슬라이드보다 카메라와 청중을 번갈아 보며 시선을 고정하는 연습이 필요합니다.")
    elif ratio > 15:
        lines.append(f"시선: 시선 이탈이 {ratio:.0f}%로 약간 높습니다. 핵심 문장을 말할 때는 카메라를 향하도록 의식해 보세요.")
    else:
        lines.append(f"시선: 시선 처리가 양호합니다 ({ratio:.0f}% 이탈).")

    if tilt > 15:
        lines.append(f"자세: 어깨 기울기가 평균 {tilt:.1f}도로 큽니다. 양발을 안정적으로 두고 어깨 높이를 맞춘 뒤 발표하세요.")
    elif tilt > 8:
        lines.append(f"자세: 어깨가 {tilt:.1f}도 기울어졌습니다. 발표 중간마다 상체 균형을 확인하세요.")
    else:
        lines.append(f"자세: 어깨 균형이 잘 유지되고 있습니다 ({tilt:.1f}도).")

    if gestures < 5:
        lines.append("제스처: 손 동작이 거의 없습니다. 핵심 포인트에서 숫자를 세거나 방향을 가리키는 제스처를 활용하면 전달력이 높아집니다.")
    elif gestures > 50:
        lines.append(f"제스처: 제스처가 {gestures}회로 많습니다. 반복적인 손동작을 줄이고 강조 지점에만 사용해 안정감을 높이세요.")
    else:
        lines.append(f"제스처: 제스처 사용이 적절합니다 ({gestures}회).")

    if blink > 40:
        lines.append(f"집중도: 눈 감음 비율이 {blink:.0f}%로 높습니다. 카메라를 향해 눈을 충분히 뜨고 발표하세요.")

    if silence > 50:
        lines.append(f"발화: 침묵 구간이 {silence:.0f}%로 많습니다. 발표 흐름이 끊기지 않도록 말할 순서와 연결 문장을 미리 연습하세요.")

    return "\n\n".join(lines)

def run_full_analysis(video_path: Path, api_key: str, on_step=None) -> dict[str, Any]:
    metrics = analyze_video(video_path, on_step)
    if on_step:
        on_step(5)
    coaching = _gemini_coaching(metrics, api_key)
    metrics["coaching"] = coaching
    return metrics
