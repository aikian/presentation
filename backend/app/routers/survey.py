import logging
import secrets
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.core.database import execute_supabase, get_supabase
from app.core.survey_db import (
    attach_survey_to_result,
    close_survey_link,
    create_survey_link,
    fetch_survey_responses,
    get_survey_link,
    insert_survey_result,
    save_survey_response
)
from app.core.weights_db import maybe_update_model
from app.middleware.auth import CurrentUser, get_current_user
from app.services.survey_analyzer import analyze_survey_csv

logger = logging.getLogger(__name__)
router = APIRouter()

SURVEY_LINK_MINUTES = 30

class Scores(BaseModel):
    question_1: int = Field(ge=1, le=5) # spm
    question_2: int = Field(ge=1, le=5) # pitch_variation
    question_3: int = Field(ge=1, le=5) # db
    question_4: int = Field(ge=1, le=5) # silence
    question_5: int = Field(ge=0, le=100) # attention_score
    
class SurveySubmit(BaseModel):
    participant_id: str = Field(min_length=8, max_length=64)
    scores: Scores
    opinion: str = Field(default="", max_length=1000)
    
class AttachBody(BaseModel):
    result_id: str
    
def check_result_owner(result_id: str, user_id: str) -> None:
    res = execute_supabase(
        lambda: get_supabase()
        .table("analysis_results")
        .select("id")
        .eq("id", result_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")
    
def get_owned_link(token: str, user_id: str) -> dict:
    link = get_survey_link(token)
    if not link or link.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="존재하지 않는 설문입니다.")
    return link

def get_open_link(token: str) -> dict:
    # 청중용: 열려 있고 만료되지 않은 링트만 통과
    link = get_survey_link(token)
    if not link:
        raise HTTPException(status_code=404, detail="존재하지 않는 설문입니다.")
    
    expires_at = datetime.fromisoformat(link["expires_at"].replace("Z", "+00:00"))
    if not link["is_open"] or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="마감된 설문입니다.")
    return link

@router.post("/links")
def create_link(current_user: CurrentUser = Depends(get_current_user)):
    # 설문 QR용 링크 발급
    token = secrets.token_urlsafe(8)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=SURVEY_LINK_MINUTES)
    
    try:
        create_survey_link(token, current_user.id, expires_at.isoformat())
    except Exception:
        logger.exception("설문 링크 생성 실패")
        raise HTTPException(status_code=500, detail="설문 링크 생성 실패")
    
    return {"token": token, "url": f"{settings.frontend_base_url}/survey/{token}"}

@router.post("/{token}/close")
def close_survey(token: str, current_user: CurrentUser = Depends(get_current_user)):
    # 설문 링크 닫기
    get_owned_link(token, current_user.id)
    try:
        close_survey_link(token)
    except Exception:
        logger.exception("설문 마감 실패")
        raise HTTPException(status_code=500, detail="설문 마감 실패")
    return {"ok": True}

@router.post("/{token}/attach")
def attach(
    token: str,
    body: AttachBody,
    current_user: CurrentUser = Depends(get_current_user)
):
    # 발표 분석 후 분석 결과와 설문을 연결
    get_owned_link(token, current_user.id)
    check_result_owner(body.result_id, current_user.id)
    try:
        attach_survey_to_result(token, body.result_id)
    except Exception:
        logger.exception("설문 연결 실패")
        raise HTTPException(status_code=500, detail="설문 연결 실패")
    return {"ok": True}

@router.post("/results/{result_id}/analyze")
async def analyze_collected_survey(
    result_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    # QR 응답을 기존의 분석 방법으로 분석해서 survey_results에 저장
    check_result_owner(result_id, current_user.id)
    
    rows = fetch_survey_responses(result_id)
    if not rows:
        raise HTTPException(status_code=400, detail="수집된 설문 응답이 없습니다.")
    
    csv_bytes = pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
    file = UploadFile(file=BytesIO(csv_bytes), filename="survey_from_qr.csv")
    
    try:
        result = await analyze_survey_csv(file, result_id, api_key=settings.gemini_api_key)
        
        if not insert_survey_result(result_id, result):
            raise RuntimeError("설문 결과 저장에 실패했습니다.")
        
        result["weight_updated"] = False
        try:
            update_result = maybe_update_model()
            result["weight_updated"] = bool(update_result and update_result.get("updated"))
        except Exception:
            logger.exception("가중치 업데이트 중 오류가 발생했습니다.")
            
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        logger.exception("QR 설문 분석 중 오류가 발생했습니다.")
        raise HTTPException(status_code=500, detail="설문 분석 오류")
    
    return {
        "message": "설문 분석 성공",
        "result_id": result_id,
        "response_count": len(rows),
        "analysis_result": result
    }
    
# 청중용 (로그인 없이, 토큰만으로 접근)
@router.get("/{token}")
def check_survey(token: str):
    # 접근하려는 설문 페이지가 열려 있는지 확인
    get_open_link(token)
    return {"open": True}

@router.post("/{token}/responses")
def submit_response(token: str, body: SurveySubmit):
    link = get_open_link(token)
    s = body.scores
    
    row = {
        "participant_id": body.participant_id,
        "spm": s.question_1,
        "pitch_variation": s.question_2,
        "db": s.question_3,
        "silence": s.question_4,
        "attention_score": s.question_5,
        "feedback": body.opinion.strip() or None
    }
    
    try:
        save_survey_response(link, row)
    except Exception:
        logger.exception("설문 응답 저장 실패")
        raise HTTPException(status_code=500, detail="설문 저장에 실패했습니다.")
    
    return {"ok": True}
