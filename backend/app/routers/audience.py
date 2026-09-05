from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File

from app.core.database import get_supabase
from app.middleware.auth import CurrentUser, get_current_user

from app.services.survey_analyzer import analyze_survey_csv

router = APIRouter()

@router.post("/upload")
async def upload_survey(
    file: UploadFile = File(...),
    result_id: str = Form(...),
    current_user: CurrentUser = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="CSV 파일만 업로드 가능합니다."
        )
    
    try: 
        result = await analyze_survey_csv(file, result_id)
        
        return {
            "message": "CSV 분석 성공",
            "result_id": result_id,
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
            detail= "CSV 분석 오류"
        )
        
@router.get("/{result_id}")
def get_audience_prediction(
    result_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    try:
        response = (
            get_supabase()
            .table("analysis_results")
            .select("*")
            .eq("id", result_id)
            .eq("user_id", current_user.id)
            .single()
            .execute()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DB 조회 실패: {e}"
        )
    
    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="분석 결과를 찾을 수 없습니다."
        )
        
    data = response.data
    details = data.get("details") or {}
    
    return {
        "result_id": result_id,
        
        # 시간순 청중의 예측 집중도
        "timeline_second": details.get(
            "timeline_second", []
        ),
        
        "timeline_minute": details.get(
            "timeline_minute", []
        ),
        
        # 총 집중도
        "attention_score": details.get(
            "attention_score", 0
        )
    }
    
'''
# 청중 집중도 분석 결과 DB에서 가져와서 표시
@router.get("/result/{presentation_id}")
def get_analysis_result(presentation_id: int):
    
    return{
        "presentaton_id": presentation_id
    }
'''

