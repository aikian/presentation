"""롤모델 영상 구간 선별 (2차).

1차에서 객석 컷과 슬라이드 사진이 "쓸 만함"으로 통과하는 문제가 있었다.
눈으로 확인한 프레임들의 특징을 재서 기준을 다시 잡았다.

  - 검출기를 FaceDetection -> FaceMesh로 바꿈.
    실제 분석 파이프라인이 FaceMesh를 쓰므로 "그 도구로 분석 가능한가"를 그대로 재는 게 맞다.
    1차 때 정상 클로즈업인데 FaceDetection이 못 잡은 프레임도 있었다.
  - 객석 컷: 비슷한 크기 얼굴이 여럿 (측정값 0.26/0.26, 0.31/0.28). 연사 샷은 항상 1명.
  - 슬라이드: 화면이 밝다 (밝기 중앙값 230). 무대는 어둡다 (3~70).
  - 롱샷: 얼굴이 화면 높이의 15% 미만. 정상 중간샷은 18% 이상.
"""
import json
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

VIDEO_DIR = Path(r"z:\대학\MIDAS종합설계\2학기\presentation\reference_data\videos")
OUT = Path(__file__).parent / "segments_v2.json"

SAMPLE_SEC = 1.0
MIN_FACE_RATIO = 0.17    # 이보다 작으면 롱샷. FaceMesh 랜드마크 정밀도가 떨어진다
SECOND_FACE_RATIO = 0.5  # 두 번째 얼굴이 첫 번째의 이 비율을 넘으면 객석 컷으로 본다
MAX_BRIGHTNESS = 120     # 밝기 중앙값이 이보다 높으면 슬라이드 화면
MIN_SEG_SEC = 10.0
MAX_GAP_SEC = 1.0        # 1차의 2초는 너무 관대해서 나쁜 구간을 이어붙였다

mp_mesh = mp.solutions.face_mesh


def face_ratios(mesh_result) -> list[float]:
    """검출된 얼굴들의 세로 크기를 화면 높이 대비 비율로."""
    out = []
    for lm in (mesh_result.multi_face_landmarks or []):
        ys = [p.y for p in lm.landmark]
        out.append(max(ys) - min(ys))
    return sorted(out, reverse=True)


def scan(video_path: Path) -> list[dict]:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = max(1, int(fps * SAMPLE_SEC))

    samples = []
    idx = 0
    with mp_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=3,
        refine_landmarks=False, min_detection_confidence=0.5,
    ) as mesh:
        while True:
            if not cap.grab():
                break
            if idx % step == 0:
                ok, frame = cap.retrieve()
                if ok:
                    small = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
                    res = mesh.process(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
                    hs = face_ratios(res)
                    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

                    first = hs[0] if hs else 0.0
                    second = hs[1] if len(hs) > 1 else 0.0
                    bright = float(np.median(gray))

                    reason = None
                    if first < MIN_FACE_RATIO:
                        reason = "롱샷/미검출"
                    elif second > first * SECOND_FACE_RATIO:
                        reason = "객석"
                    elif bright > MAX_BRIGHTNESS:
                        reason = "슬라이드"

                    samples.append({
                        "sec": round(idx / fps, 1),
                        "ok": reason is None,
                        "reason": reason,
                        "ratio": round(first, 3),
                        "bright": bright,
                    })
            idx += 1
    cap.release()
    return samples


def to_segments(samples: list[dict]) -> list[dict]:
    segs, start, last_ok = [], None, None
    for s in samples:
        if s["ok"]:
            if start is None:
                start = s["sec"]
            last_ok = s["sec"]
        elif start is not None and s["sec"] - last_ok > MAX_GAP_SEC:
            segs.append({"start": start, "end": last_ok})
            start = None
    if start is not None:
        segs.append({"start": start, "end": last_ok})

    return [
        {**s, "dur": round(s["end"] - s["start"], 1)}
        for s in segs if s["end"] - s["start"] >= MIN_SEG_SEC
    ]


result = {}
for video in sorted(VIDEO_DIR.glob("*.mp4")):
    print(f"분석 중: {video.name}", flush=True)
    samples = scan(video)
    segs = to_segments(samples)
    span = samples[-1]["sec"] if samples else 0
    total = round(sum(s["dur"] for s in segs), 1)

    rejected = {}
    for s in samples:
        if s["reason"]:
            rejected[s["reason"]] = rejected.get(s["reason"], 0) + 1

    result[video.stem] = {
        "duration_sec": span,
        "usable_sec": total,
        "usable_pct": round(total / span * 100, 1) if span else 0,
        "segment_count": len(segs),
        "rejected": rejected,
        "segments": segs,
    }
    print(f"  쓸 만함 {total:.0f}초 / {span:.0f}초 ({result[video.stem]['usable_pct']}%), 구간 {len(segs)}개", flush=True)
    print(f"  제외 사유: {rejected}", flush=True)

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("저장:", OUT.name)
