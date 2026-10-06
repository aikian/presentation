from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.database import get_supabase
from app.middleware.auth import CurrentUser, get_current_user
from app.services.report_generator import generate_report

router = APIRouter()

_HISTORY_COLS = (
    "id,gaze_away_ratio,shoulder_tilt_avg,gesture_count,"
    "ear_blink_ratio,silence_ratio,coaching,created_at,"
    "score_gaze,score_pose,score_gesture,score_voice,score_time,score_total,"
    "elapsed_sec,goal_sec"
)


@router.get("")
def get_history(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    current_user: CurrentUser = Depends(get_current_user),
):
    offset = (page - 1) * limit
    try:
        res = (
            get_supabase()
            .table("analysis_results")
            .select(_HISTORY_COLS)
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"items": res.data, "page": page, "limit": limit}
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


@router.get("/{result_id}")
def get_result(result_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """분석 결과 하나를 details까지 통째로 돌려준다.

    결과 화면은 지금까지 업로드 job의 응답만 보고 그렸다.
    job은 서버 메모리에 있어서 새로고침하거나 서버가 재시작되면 사라지고,
    히스토리에서 지난 결과를 다시 열 수도 없었다.
    화면이 이 API를 쓰면 결과 id만 있으면 언제든 같은 화면을 다시 그릴 수 있다.

    주의: 이 라우트는 /{result_id} 형태라 /growth 같은 고정 경로보다 뒤에 있어야 한다.
    먼저 선언하면 FastAPI가 "growth"를 result_id로 받아버린다.
    """
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
        raise HTTPException(500, f"결과 조회 실패: {e}")

    if not res.data:
        raise HTTPException(404, "결과를 찾을 수 없습니다.")

    return res.data[0]
