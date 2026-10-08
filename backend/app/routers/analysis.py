import asyncio
import json
import logging
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import get_supabase, save_attention_prediction
from app.middleware.auth import CurrentUser, get_current_user
from app.services.analysis_schema import build_audio_block, build_details
from app.services.rolemodel import compare
from app.services.score_calculator import calculate_scores
from app.services.video_analyzer import run_full_analysis
from app.services.audio_features import analyze_audio_features
from app.services.predict_concentration import analyze_audience

logger = logging.getLogger(__name__)
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
    rolemodel_id: str | None = None,
):
    def update_step(step: int):
        _jobs[job_id]["step"] = step

    try:
        result = run_full_analysis(video_path, settings.gemini_api_key, update_step)

        if elapsed_sec is not None:
            result["elapsed_sec"] = elapsed_sec

        scores = calculate_scores(result, goal_sec)
        result.update(scores)
        
        # 음성기반 청중의 집중도 추정
        attention_result = None
        if settings.enable_audio_analysis:
            try:
                audio_metrics = result.get("audio_metrics")
                audio_features = analyze_audio_features(video_path)
                
                if audio_metrics and audio_features:
                    attention_result = analyze_audience(audio_metrics, audio_features)
                    if attention_result.get("status") != "SUCCESS":
                        logger.warning(
                            "집중도 예측 실패 (code=%s): %s",
                            attention_result.get("error_code"),
                            attention_result.get("message")
                        )
                        attention_result = None
                else:
                    logger.info("집중도 예측 생략: audio_metrics=%s, audio_features=%s",bool(audio_metrics), bool(audio_features))

            except Exception:
                logger.warning("음성 기반 집중도 예측 실패", exc_info=True)
        else:
            logger.info("enable_audio_analysis가 꺼져 있어 집중도 예측을 건너뜁니다")
                    

        # 롤모델 비교. 연사 데이터를 못 읽어도 분석 결과는 그대로 살린다.
        try:
            audio_block = build_audio_block(
                result.get("audio_metrics"), result.get("duration_sec")
            )
            if audio_block:
                refs = get_supabase().table("reference_speakers").select("*").execute().data
                # 음성 요약에 표정 지표를 합쳐서 비교한다. 연사 쪽도 같은 함수로 잰 값이다.
                user_summary = {
                    **audio_block["summary"],
                    "smile_ratio": result.get("smile_ratio"),
                    "expression_change_std": result.get("expression_change_std"),
                }
                result["rolemodel_comparison"] = compare(
                    user_summary, refs or [], rolemodel_id
                )
        except Exception:
            logger.warning("롤모델 비교를 건너뜁니다", exc_info=True)

        # 팀 공유 스키마(docs/schema/) 형식. analysis_results.details에 통째로 저장한다.
        details = build_details(
            result,
            duration_sec=result.get("duration_sec"),
            frame_interval_sec=settings.frame_interval_sec,
            target_time_sec=goal_sec,
        )

        # details를 job 응답에도 넣는다. 결과 화면 탭이 평면 컬럼 대신 details를 읽는다.
        # DB 저장이 실패해도 화면은 그려져야 하므로 저장 전에 담는다.
        result["details"] = details

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
                "problem_frames": result.get("problem_frames", []),
                "score_gaze": scores["score_gaze"],
                "score_pose": scores["score_pose"],
                "score_gesture": scores["score_gesture"],
                "score_voice": scores["score_voice"],
                "score_time": scores["score_time"],
                "score_total": scores["score_total"],
                "details": details,
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
                        logger.warning("세션 저장 실패", exc_info=True)
                    
                # 청중 집중도 결과 저장   
                if attention_result:
                    try:
                        save_attention_prediction(saved_id, attention_result)
                    except Exception:
                        logger.warning("집중도 예측 결과 저장 실패", exc_info=True)
                else:
                    logger.info("집중도 예측 결과가 없어 저장하지 않습니다")
        except Exception:
            # 분석은 끝났으니 화면에는 결과를 보여준다. 다만 조용히 묻으면
            # "분석은 됐는데 히스토리에 없다"는 증상의 원인을 찾을 수 없다.
            logger.warning("분석 결과 저장 실패 (job %s)", job_id, exc_info=True)
    except Exception as e:
        _jobs[job_id] = {"status": "error", "step": _jobs[job_id].get("step", 0), "error": str(e)}
    finally:
        video_path.unlink(missing_ok=True)


@router.get("/speakers")
def list_speakers():
    """고를 수 있는 롤모델 연사 목록.

    발표를 올릴 때 "이 사람처럼 말하고 싶다"를 고를 수 있게 한다.
    고르지 않으면 연사 전체의 범위를 기준선으로 쓴다.
    """
    try:
        res = (
            get_supabase()
            .table("reference_speakers")
            .select("id,name,affiliation,source,title,audio_summary")
            .order("name")
            .execute()
        )
    except Exception:
        logger.warning("연사 목록 조회 실패", exc_info=True)
        return JSONResponse({"speakers": []})

    return JSONResponse({"speakers": res.data or []})


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    goal_sec: float | None = Form(None),
    elapsed_sec: float | None = Form(None),
    slide_log: str | None = Form(None),
    rolemodel_id: str | None = Form(None),
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
        rolemodel_id or None,
    )

    return JSONResponse({"job_id": job_id})


@router.get("/{job_id}")
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "job을 찾을 수 없습니다")
    return JSONResponse(job)
