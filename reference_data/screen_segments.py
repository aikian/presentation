"""롤모델 영상에서 연사가 충분히 크게, 오래 잡힌 구간만 골라낸다.

세바시 같은 강연 영상은 카메라가 자주 바뀐다. 객석 컷, 슬라이드 화면, 전신 롱샷이
섞여 있는데 이런 구간에서는 시선·표정 분석이 불가능하거나 엉뚱한 얼굴을 잡는다.

판정 기준은 오판한 프레임과 정상 프레임을 눈으로 확인하고 특징을 재서 정했다.

  - 롱샷: 얼굴이 화면 높이의 17% 미만. 정상 중간샷은 18% 이상이었다.
  - 객석: 비슷한 크기 얼굴이 여럿 (실측 0.26/0.26, 0.31/0.28). 연사 샷은 항상 1명.
  - 슬라이드: 화면이 밝다 (밝기 중앙값 230). 무대는 어둡다 (3~70).

검출기는 FaceMesh를 쓴다. 실제 분석 파이프라인이 FaceMesh를 쓰므로
"그 도구로 분석 가능한가"를 그대로 재는 것이 맞다.
처음엔 FaceDetection을 썼는데 정상 클로즈업을 놓치는 경우가 있었다.

**남은 한계 (약 3%)**: 객석인데 앞줄 한 명만 정면이라 FaceMesh가 얼굴을 1개만
검출하면 연사 샷으로 통과한다. 배경 밝기나 어두운 픽셀 비율로는 구분되지 않는다
(객석 27.3% vs 정상 28.3%). 제대로 고치려면 얼굴 지문으로 연사 본인인지 확인해야 한다.
"""
import json
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

VIDEO_DIR = Path(__file__).parent / "videos"
OUT = Path(__file__).parent / "segments.json"

SAMPLE_SEC = 0.5         # 1초로 재면 짧은 컷을 놓치고 구간 경계가 최대 1초 어긋난다
MIN_FACE_RATIO = 0.17    # 이보다 작으면 롱샷. FaceMesh 랜드마크 정밀도가 떨어진다
SECOND_FACE_RATIO = 0.5  # 두 번째 얼굴이 첫 번째의 이 비율을 넘으면 객석 컷으로 본다
MAX_BRIGHTNESS = 120     # 밝기 중앙값이 이보다 높으면 슬라이드 화면
MIN_SEG_SEC = 10.0
MAX_GAP_SEC = 1.0        # 잠깐 얼굴을 놓친 것과 실제 컷 전환을 구분하는 여유

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
    """좋은 샘플이 이어지는 구간으로 묶는다.

    경계는 마지막 좋은 샘플과 첫 나쁜 샘플의 중간으로 잡는다.
    실제 컷 전환은 그 사이 어딘가라, 좋은 샘플 시각을 그대로 쓰면
    컷 직전의 나쁜 화면이 최대 한 샘플 간격만큼 구간 안에 남는다.
    """
    segs = []
    start = None
    last_ok = None
    last_ok_i = -1

    for i, s in enumerate(samples):
        if s["ok"]:
            if start is None:
                prev_bad = i > 0 and not samples[i - 1]["ok"]
                start = (samples[i - 1]["sec"] + s["sec"]) / 2 if prev_bad else s["sec"]
            last_ok, last_ok_i = s["sec"], i
        elif start is not None and s["sec"] - last_ok > MAX_GAP_SEC:
            nxt = samples[last_ok_i + 1]["sec"] if last_ok_i + 1 < len(samples) else last_ok
            segs.append({"start": round(start, 1), "end": round((last_ok + nxt) / 2, 1)})
            start = None

    if start is not None:
        segs.append({"start": round(start, 1), "end": round(last_ok, 1)})

    return [
        {**s, "dur": round(s["end"] - s["start"], 1)}
        for s in segs if s["end"] - s["start"] >= MIN_SEG_SEC
    ]


def screen(video_path: Path) -> dict:
    """영상 한 편을 선별해 결과 요약을 돌려준다."""
    samples = scan(video_path)
    segs = to_segments(samples)
    span = samples[-1]["sec"] if samples else 0
    total = round(sum(s["dur"] for s in segs), 1)

    rejected: dict[str, int] = {}
    for s in samples:
        if s["reason"]:
            rejected[s["reason"]] = rejected.get(s["reason"], 0) + 1

    return {
        "duration_sec": span,
        "usable_sec": total,
        "usable_pct": round(total / span * 100, 1) if span else 0,
        "segment_count": len(segs),
        "rejected": rejected,
        "segments": segs,
    }


# 다른 스크립트가 scan·to_segments·screen만 가져다 쓸 수 있도록,
# 전체 실행은 이 파일을 직접 돌릴 때만 한다.
if __name__ == "__main__":
    result = {}
    for video in sorted(VIDEO_DIR.glob("*.mp4")):
        print(f"분석 중: {video.name}", flush=True)
        r = screen(video)
        result[video.stem] = r
        print(f"  쓸 만함 {r['usable_sec']:.0f}초 / {r['duration_sec']:.0f}초 "
              f"({r['usable_pct']}%), 구간 {r['segment_count']}개", flush=True)
        print(f"  제외 사유: {r['rejected']}", flush=True)

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("저장:", OUT.name)
