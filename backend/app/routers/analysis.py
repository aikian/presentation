import asyncio
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import get_supabase
from app.middleware.auth import CurrentUser, get_current_user
from app.services.video_analyzer import run_full_analysis

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}
MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024

_jobs: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=2)


def _run_job(job_id: str, video_path: Path, user_id: str):
    def update_step(step: int):
        _jobs[job_id]["step"] = step

    try:
        result = run_full_analysis(video_path, settings.gemini_api_key, update_step)
        _jobs[job_id] = {"status": "done", "step": 5, "result": result}

        try:
            result_id = uuid.uuid4().hex
            sb_res = get_supabase().table("analysis_results").insert({
                "id": result_id,
                "user_id": user_id,
                "gaze_away_ratio": result.get("gaze_away_ratio", 0),
                "shoulder_tilt_avg": result.get("shoulder_tilt_avg", 0),
                "gesture_count": result.get("gesture_count", 0),
                "ear_blink_ratio": result.get("ear_blink_ratio", 0),
                "silence_ratio": result.get("silence_ratio", 0),
                "coaching": result.get("coaching", ""),
            }).execute()
            if sb_res.data:
                _jobs[job_id]["result_id"] = sb_res.data[0]["id"]
        except Exception:
            pass  # Supabase 미설정 시 무시
    except Exception as e:
        _jobs[job_id] = {"status": "error", "step": _jobs[job_id].get("step", 0), "error": str(e)}
    finally:
        video_path.unlink(missing_ok=True)


@router.post("/upload")
async def upload_video(file: UploadFile = File(...), current_user: CurrentUser = Depends(get_current_user)):
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

    _jobs[job_id] = {"status": "pending", "step": 0}
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_job, job_id, tmp_path, current_user.id)

    return JSONResponse({"job_id": job_id})


@router.get("/{job_id}")
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "job을 찾을 수 없습니다")
    return JSONResponse(job)
