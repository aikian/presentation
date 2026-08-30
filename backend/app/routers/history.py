from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.database import get_supabase
from app.middleware.auth import CurrentUser, get_current_user
from app.services.report_generator import generate_report
# [신규 추가] 성장 분석 스키마 빌더
from app.services.growth_schema import build_growth_report

router = APIRouter()

_HISTORY_COLS = (
    "id,gaze_away_ratio,shoulder_tilt_avg,gesture_count,"
    "ear_blink_ratio,silence_ratio,coaching,created_at,"
    "score_gaze,score_pose,score_gesture,score_time,score_total,"
    "elapsed_sec,goal_sec"
)

# [신규 추가] growth 계산에는 details(schema v0.1)까지 필요해서 컬럼을 추가로 조회한다.
_GROWTH_COLS = _HISTORY_COLS + ",details"


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


# ===================== [신규 추가] 발표 성장 분석(History 강화) ===================== #
# 기능_추가_제안서.hwp "기능 2. 발표 성장 분석" + 계획서 1~2주차 완료 기준
# ("샘플 영상 1개를 넣으면 각 모듈이 스키마 형식의 JSON 조각을 출력한다")에 대응.
#
# 담당(계획서 Roles): 게시판·성장 제안자 — feature/history-db
# 읽는 데이터: 여러 세션의 scores · summary · habits
# 쓰는 데이터: 성장 리포트(JSON) — 이력 DB 테이블은 기존 analysis_results 재사용
@router.get("/growth")
def get_growth_report(
    limit: int = Query(10, ge=2, le=50, description="비교에 사용할 최근 발표 개수"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """최근 발표 이력을 스키마 v0.1의 growth JSON 조각으로 변환해 돌려준다.

    프론트엔드 History/Growth 화면에서 이 응답을 그대로 Chart.js에 넣어
    그래프를 그리고, feedback 문구를 그대로 표시하면 된다.
    """
    try:
        res = (
            get_supabase()
            .table("analysis_results")
            .select(_GROWTH_COLS)
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"성장 리포트 조회 실패: {e}")

    # build_growth_report()가 곧 "계획서에 적힌 JSON 조각을 출력하는 코드"에 해당한다.
    return build_growth_report(res.data or [])
# =================================================================================== #
