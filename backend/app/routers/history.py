from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.core.database import get_supabase
from app.middleware.auth import CurrentUser, get_current_user
from app.services.report_generator import generate_report

router = APIRouter()


@router.get("")
def get_history(current_user: CurrentUser = Depends(get_current_user)):
    try:
        res = (
            get_supabase()
            .table("analysis_results")
            .select("id,gaze_away_ratio,shoulder_tilt_avg,gesture_count,coaching,created_at")
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data
    except Exception as e:
        raise HTTPException(500, f"히스토리 조회 실패: {e}")


@router.get("/{result_id}/pdf")
def download_pdf(result_id: str, current_user: CurrentUser = Depends(get_current_user)):
    try:
        res = (
            get_supabase()
            .table("analysis_results")
            .select("*")
            .eq("id", result_id)
            .eq("user_id", current_user.id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"DB 조회 실패: {e}")

    if not res.data:
        raise HTTPException(404, "결과를 찾을 수 없습니다.")

    pdf_bytes = generate_report(res.data[0])
    filename = f"presentationcoach_report_{result_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
