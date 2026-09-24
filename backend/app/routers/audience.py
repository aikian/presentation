import logging

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File

from app.core.database import get_supabase
from app.core.survey_db import insert_survey_result
from app.middleware.auth import CurrentUser, get_current_user
from app.core.weights_db import maybe_update_model

from app.services.survey_analyzer import analyze_survey_csv

logger = logging.getLogger(__name__)
router = APIRouter()

def check_result_owner(result_id: str, user_id: str) -> None:
    res = (
        get_supabase()
        .table("analysis_results")
        .select("id")
        .eq("id", result_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    
    if not res.data:
        raise HTTPException(
            status_code=404,
            detail="분석 결과를 찾을 수 없습니다."
        )
        
@router.post("/uploadCSV")
async def upload_survey(
    file: UploadFile = File(...),
    result_id: str = Form(...),
    current_user: CurrentUser = Depends(get_current_user)
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="CSV 파일만 업로드 가능합니다."
        )
        
    check_result_owner(result_id, current_user.id)
    
    try:
        result = await analyze_survey_csv(file, result_id)
        
        if not insert_survey_result(result_id, result):
            raise RuntimeError("설문 결과 저장에 실패했습니다.")
        
        result["weight_updated"] = False
        try:
            update_result = maybe_update_model()
            result["weight_updated"] = bool(update_result and update_result.get("updated"))
        except Exception:
            logger.exception("가중치 업데이트 중 오류가 발생했습니다")

    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=str(ve)
        )
    except Exception:
        logger.exception("설문 CSV 처리 중 오류가 발생했습니다")
        raise HTTPException(
            status_code=500,
            detail="CSV 분석 오류"
        )
        
    return {
        "message": "CSV 분석 성공",
        "result_id": result_id,
        "filename": file.filename,
        "analysis_result": result
    }

@router.get("/{result_id}/survey")
def get_survey_result(
    result_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    check_result_owner(result_id, current_user.id)
    
    try:
        res = (
            get_supabase()
            .table("survey_results")
            .select("participant_count,average_attention_score,feature_means,feedbacks,learning_data_available,created_at")
            .eq("result_id", result_id)
            .limit(1)
            .execute()
        )
    
    except Exception:
        logger.exception("설문 결과 조회 실패")
        raise HTTPException(
            status_code=500,
            detail="DB 조회 실패"
        )
        
    return {
        "result_id": result_id,
        "survey_result": res.data[0] if res.data else None
    }
    
@router.get("/{result_id}/attention")
def get_audience_prediction(
    result_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    check_result_owner(result_id, current_user.id)
    try:
        res = (
            get_supabase()
            .table("attention_predictions")
            .select("attention_score,timeline_second,timeline_minute,status,created_at")
            .eq("result_id", result_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("집중도 예측 결과 조회 실패")
        raise HTTPException(
            status_code=500,
            detail="DB 조회 실패"
        )

    if not res.data:
        raise HTTPException(
            status_code=404,
            detail="분석 결과를 찾을 수 없습니다."
        )

    data = res.data[0]

    return {
        "result_id": result_id,
        "status": data.get("status"),
        "timeline_second": data.get("timeline_second", []),
        "timeline_minute": data.get("timeline_minute", []),
        "attention_score": data.get("attention_score", 0)
    }