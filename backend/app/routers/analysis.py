import asyncio
import json
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import get_supabase
from app.middleware.auth import CurrentUser, get_current_user
from app.services.score_calculator import calculate_scores
from app.services.video_analyzer import run_full_analysis

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}
MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024

_jobs: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=2)


def _run_job(
    job_id: str,
    video_path: Path,
    user_id: str,
    goal_sec: float | None,
    elapsed_sec: float | None,
    slide_log: list | None,
):
    def update_step(step: int):
        _jobs[job_id]["step"] = step

    try:
        result = run_full_analysis(video_path, settings.gemini_api_key, update_step)

        if elapsed_sec is not None:
            result["elapsed_sec"] = elapsed_sec

        scores = calculate_scores(result, goal_sec)
        result.update(scores)

        _jobs[job_id] = {"status": "done", "step": 5, "result": result}

        try:
            result_id = uuid.uuid4().hex
            sb_payload = {
                "id": result_id,
                "user_id": user_id,
                "gaze_away_ratio": result.get("gaze_away_ratio", 0),
                "shoulder_tilt_avg": result.get("shoulder_tilt_avg", 0),
                "gesture_count": result.get("gesture_count", 0),
                "ear_blink_ratio": result.get("ear_blink_ratio", 0),
                "silence_ratio": result.get("silence_ratio", 0),
                "coaching": result.get("coaching", ""),
                "score_gaze": scores["score_gaze"],
                "score_pose": scores["score_pose"],
                "score_gesture": scores["score_gesture"],
                "score_time": scores["score_time"],
                "score_total": scores["score_total"],
            }
            if elapsed_sec is not None:
                sb_payload["elapsed_sec"] = elapsed_sec
            if goal_sec is not None:
                sb_payload["goal_sec"] = goal_sec

            sb_res = get_supabase().table("analysis_results").insert(sb_payload).execute()
            if sb_res.data:
                saved_id = sb_res.data[0]["id"]
                _jobs[job_id]["result_id"] = saved_id

                if slide_log and goal_sec is not None:
                    try:
                        session_id = uuid.uuid4().hex
                        get_supabase().table("sessions").insert({
                            "session_id": session_id,
                            "user_id": user_id,
                            "slide_log": slide_log,
                            "target_time": int(goal_sec),
                        }).execute()
                    except Exception:
                        pass
        except Exception:
            pass
    except Exception as e:
        _jobs[job_id] = {"status": "error", "step": _jobs[job_id].get("step", 0), "error": str(e)}
    finally:
        video_path.unlink(missing_ok=True)


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    goal_sec: float | None = Form(None),
    elapsed_sec: float | None = Form(None),
    slide_log: str | None = Form(None),
    current_user: CurrentUser = Depends(get_current_user),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"지원 형식: MP4, MOV, AVI, WebM. 받은 형식: {suffix}")

    job_id = uuid.uuid4().hex
    tmp_path = Path(settings.upload_dir) / f"{job_id}{suffix}"

    try:
        with tmp_path.open("wb") as f:
            size = 0
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    tmp_path.unlink(missing_ok=True)
                    raise HTTPException(413, "파일 크기 초과")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(500, str(e))

    parsed_log = None
    if slide_log:
        try:
            parsed_log = json.loads(slide_log)
        except Exception:
            pass

    _jobs[job_id] = {"status": "pending", "step": 0}
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor, _run_job,
        job_id, tmp_path, current_user.id, goal_sec, elapsed_sec, parsed_log,
    )

    return JSONResponse({"job_id": job_id})


@router.get("/{job_id}")
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "job을 찾을 수 없습니다")
    return JSONResponse(job)
