from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, File

from app.core.database import get_supabase
from app.core.survey_db import insert_survey_result, insert_survey_group_means
from app.core.weights_db import maybe_update_group_model
from app.middleware.auth import CurrentUser, get_current_user

from app.services.survey_analyzer import analyze_survey_csv

router = APIRouter()


def _retrain_groups():
    for group in ("major", "non_major"):
        maybe_update_group_model(group)


@router.post("/upload")
async def upload_survey(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session_id: str = Form(...),
    current_user: CurrentUser = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="CSV 파일만 업로드 가능합니다."
        )

    try:
        result = await analyze_survey_csv(file, session_id)

        saved_survey = insert_survey_result(session_id, result)
        if saved_survey:
            insert_survey_group_means(saved_survey["id"], session_id, result["group_means"])

        background_tasks.add_task(_retrain_groups)

        return {
            "message": "CSV 분석 성공",
            "session_id": session_id,
            "filename": file.filename,
            "analysis_result": result
        }

    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="CSV 분석 오류"
        )


@router.get("/{session_id}")
def get_audience_prediction(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    try:
        res = (
            get_supabase()
            .table("attention_predictions")
            .select("attention_score,timeline_second,timeline_minute,status,created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DB 조회 실패: {e}"
        )

    if not res.data:
        raise HTTPException(
            status_code=404,
            detail="분석 결과를 찾을 수 없습니다."
        )

    data = res.data[0]

    return {
        "session_id": session_id,
        "timeline_second": data.get("timeline_second", []),
        "timeline_minute": data.get("timeline_minute", []),
        "attention_score": data.get("attention_score", 0)
    }