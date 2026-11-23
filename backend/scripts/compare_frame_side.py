"""프레임 축소(MAX_FRAME_SIDE)가 분석 시간, 메모리, 점수에 주는 영향을 재는 실험 스크립트.

같은 영상을 해상도 단계별로 돌려서 단계별 시간, 최대 메모리(RSS), 지표, 점수를 비교한다.
운영에 축소를 켤지 정하는 근거 자료를 만드는 용도라, 결과는 JSON으로 남긴다.
해상도마다 별도 프로세스로 돌려서 메모리 최대치가 서로 섞이지 않게 한다.

사용 예 (backend 폴더에서, 음성 분석은 .env에서 ENABLE_AUDIO_ANALYSIS=false 로 꺼 둔다):
    PYTHONPATH=. python scripts/compare_frame_side.py 영상1.mp4 영상2.mp4 --sides 0 960 640 --out 결과.json

해상도 0은 원본 그대로를 뜻한다.
"""
import argparse
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

STAGE_NAMES = {1: "extract", 2: "face", 3: "pose", 4: "hands_habits", 5: "finish"}

METRIC_KEYS = [
    "face_detected_ratio", "gaze_away_ratio", "shoulder_tilt_avg",
    "gesture_per_min", "gesture_valid_ratio", "smile_ratio", "duration_sec",
]
SCORE_KEYS = ["score_gaze", "score_pose", "score_gesture", "score_total"]


def _peak_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS는 바이트, 리눅스는 KB 단위다.
    return round(usage / (1024 * 1024) if sys.platform == "darwin" else usage / 1024, 1)


def run_once(video: Path, side: int) -> dict:
    """한 프로세스 안에서 한 설정만 돌린다. 호출 쪽(main)이 설정마다 새 프로세스를 띄운다."""
    from app.core.config import settings
    from app.services.score_calculator import calculate_scores
    from app.services import video_analyzer

    try:
        settings.max_frame_side = side
    except ValueError:
        # 축소 옵션이 없는 옛 버전(비교 기준)에서는 원본(0)만 돌린다.
        if side != 0:
            raise
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
        "video": video.name,
        "side": side,
        "total_sec": round(t_end - t0, 2),
        "peak_rss_mb": _peak_rss_mb(),
        "stages": stages,
        "metrics": {k: result.get(k) for k in METRIC_KEYS},
        "scores": {k: scores.get(k) for k in SCORE_KEYS},
        "frames": len(result.get("video_timeline") or []),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--sides", nargs="+", type=int, default=[0, 960, 640])
    ap.add_argument("--out", default="frame_side_results.json")
    ap.add_argument("--single", action="store_true", help="내부용. 한 설정만 돌리고 JSON 한 줄을 출력한다.")
    args = ap.parse_args()

    if args.single:
        r = run_once(Path(args.videos[0]), args.sides[0])
        print("RESULT " + json.dumps(r, ensure_ascii=False))
        return

    results = []
    for v in args.videos:
        for side in args.sides:
            print(f"[run] {Path(v).name} side={side}", file=sys.stderr, flush=True)
            proc = subprocess.run(
                [sys.executable, __file__, v, "--sides", str(side), "--single"],
                capture_output=True, text=True, env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", ".")},
            )
            line = next((l for l in proc.stdout.splitlines() if l.startswith("RESULT ")), None)
            if line is None:
                print(proc.stderr[-2000:], file=sys.stderr)
                raise SystemExit(f"실행 실패: {v} side={side}")
            r = json.loads(line[len("RESULT "):])
            results.append(r)
            print(json.dumps(r, ensure_ascii=False), flush=True)
            Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2))

    # 원본(side=0) 대비 차이 요약
    print("\nvideo | side | total_sec | peak_rss_mb | gaze | posture | gesture | total | d_gaze | d_posture | d_gesture | d_total")
    base = {r["video"]: r for r in results if r["side"] == 0}
    for r in results:
        b = base.get(r["video"])
        s, bs = r["scores"], (b or {}).get("scores", {})

        def d(k):
            if not b or s.get(k) is None or bs.get(k) is None:
                return "-"
            return f"{s[k] - bs[k]:+d}"

        print(f"{r['video']} | {r['side']} | {r['total_sec']} | {r['peak_rss_mb']} | {s['score_gaze']} | {s['score_pose']} | "
              f"{s['score_gesture']} | {s['score_total']} | {d('score_gaze')} | {d('score_pose')} | "
              f"{d('score_gesture')} | {d('score_total')}")


if __name__ == "__main__":
    main()
