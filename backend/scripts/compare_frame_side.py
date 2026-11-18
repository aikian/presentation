"""프레임 축소(MAX_FRAME_SIDE)가 분석 시간과 점수에 주는 영향을 재는 실험 스크립트.

같은 영상을 해상도 단계별로 돌려서 단계별 시간, 지표, 점수를 비교한다.
운영에 축소를 켤지 정하는 근거 자료를 만드는 용도라, 결과는 JSON으로 남긴다.

사용 예 (backend 폴더에서, 음성 분석은 .env에서 ENABLE_AUDIO_ANALYSIS=false 로 꺼 둔다):
    PYTHONPATH=. python scripts/compare_frame_side.py 영상1.mp4 영상2.mp4 --sides 0 960 640 480 --out 결과.json

해상도 0은 원본 그대로를 뜻한다.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from app.core.config import settings
from app.services.score_calculator import calculate_scores
from app.services import video_analyzer

STAGE_NAMES = {1: "extract", 2: "face", 3: "pose", 4: "hands_habits", 5: "finish"}

METRIC_KEYS = [
    "face_detected_ratio", "gaze_away_ratio", "shoulder_tilt_avg",
    "gesture_per_min", "gesture_valid_ratio", "smile_ratio", "duration_sec",
]
SCORE_KEYS = ["score_gaze", "score_posture", "score_gesture", "score_total"]


def run_once(video: Path, side: int) -> dict:
    settings.max_frame_side = side
    stamps: dict[int, float] = {}

    def on_step(n: int):
        stamps[n] = time.perf_counter()

    t0 = time.perf_counter()
    result = video_analyzer.run_full_analysis(video, api_key="", on_step=on_step)
    t_end = time.perf_counter()
    scores = calculate_scores(result, None)

    stages = {}
    order = sorted(stamps)
    for a, b in zip(order, order[1:]):
        stages[STAGE_NAMES[a]] = round(stamps[b] - stamps[a], 2)
    if order:
        stages[STAGE_NAMES[order[-1]]] = round(t_end - stamps[order[-1]], 2)

    return {
        "side": side,
        "total_sec": round(t_end - t0, 2),
        "stages": stages,
        "metrics": {k: result.get(k) for k in METRIC_KEYS},
        "scores": {k: scores.get(k) for k in SCORE_KEYS},
        "frames": len(result.get("video_timeline") or []),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--sides", nargs="+", type=int, default=[0, 960, 640, 480])
    ap.add_argument("--out", default="frame_side_results.json")
    args = ap.parse_args()

    results = []
    for v in args.videos:
        video = Path(v)
        for side in args.sides:
            print(f"[run] {video.name} side={side}", file=sys.stderr, flush=True)
            r = run_once(video, side)
            r["video"] = video.name
            results.append(r)
            print(json.dumps(r, ensure_ascii=False), flush=True)
            Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2))

    # 원본(side=0) 대비 차이 요약
    print("\nvideo | side | total_sec | gaze | posture | gesture | total | d_gaze | d_posture | d_gesture | d_total")
    base = {}
    for r in results:
        if r["side"] == 0:
            base[r["video"]] = r
    for r in results:
        b = base.get(r["video"])
        s, bs = r["scores"], (b or {}).get("scores", {})

        def d(k):
            if not b or s.get(k) is None or bs.get(k) is None:
                return "-"
            return f"{s[k] - bs[k]:+d}"

        print(f"{r['video']} | {r['side']} | {r['total_sec']} | {s['score_gaze']} | {s['score_posture']} | "
              f"{s['score_gesture']} | {s['score_total']} | {d('score_gaze')} | {d('score_posture')} | "
              f"{d('score_gesture')} | {d('score_total')}")


if __name__ == "__main__":
    main()
