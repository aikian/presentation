import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.config import settings
from app.core.database import get_supabase
from app.middleware.auth import CurrentUser, get_current_user
from app.services.growth_feedback import generate_growth_feedback
from app.services.growth_schema import build_growth_report
from app.services.report_generator import generate_report

logger = logging.getLogger(__name__)

router = APIRouter()

_HISTORY_COLS = (
    "id,gaze_away_ratio,shoulder_tilt_avg,gesture_count,"
    "ear_blink_ratio,silence_ratio,coaching,created_at,"
    "score_gaze,score_pose,score_gesture,score_time,score_total,"
    "elapsed_sec,goal_sec"
)

# growth 계산에는 details(schema v0.1)까지 필요해서 컬럼을 추가로 조회한다.
_GROWTH_COLS = _HISTORY_COLS + ",details"

# [2026-09-22 수정] 슬래시가 붙은 요청(/api/history/)도 같은 핸들러로 받는다.
# 리다이렉트가 일어나면서 Authorization 헤더가 떨어져 목록이 비는 경우를 막는다.
@router.get("")
@router.get("/")
def get_history(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """발표 기록 목록. 기록은 삭제하지 않으므로 여기서 안 보이면 조회에 실패한 것이다."""
    offset = (page - 1) * limit
    try:
        res = (
            get_supabase()
            .table("analysis_results")
            .select(_HISTORY_COLS, count="exact")
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except Exception as e:
        # [2026-09-22 수정] 예전에는 프론트가 이 에러를 조용히 삼켜서
        # "기록이 없습니다" 화면으로 보였다. 이제 원인이 그대로 드러난다.
        logger.exception("history query failed (user=%s)", current_user.id)
        raise HTTPException(500, f"히스토리 조회 실패: {e}")

    items = res.data or []
    # total은 DB에 실제로 몇 건이 남아 있는지 보여 주는 값이다.
    # 화면은 비었는데 total이 0보다 크면 = 기록은 살아 있고 표시 쪽 문제다.
    total = getattr(res, "count", None)
    return {"items": items, "page": page, "limit": limit, "total": total}

# ===================== 발표 성장 분석(History 강화) ===================== #
# ※ '/{result_id}/pdf'와 경로 모양이 달라 충돌하지 않지만, 읽기 쉽도록 위쪽에 둔다.
@router.get("/growth")
def get_growth_report(
    limit: int = Query(10, ge=2, le=50, description="비교에 사용할 최근 발표 개수"),
    ai: bool = Query(True, description="false면 AI 호출 없이 규칙 기반 피드백만 반환"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """최근 발표 이력을 스키마 v0.1의 growth JSON 조각으로 변환해 돌려준다.

    프론트 Growth 화면은 growth.trend를 그래프에, compare_with_previous.metrics를 비교표에,
    feedback을 AI 피드백 영역에 그대로 표시하면 된다.
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

    sessions = res.data or []

    # build_growth_report()가 곧 "계획서에 적힌 JSON 조각을 출력하는 코드"에 해당한다.
    report = build_growth_report(sessions)
    growth = report["growth"]

    # 발표 2회 이상이면 AI 성장 피드백으로 교체. 실패하면 규칙 기반 피드백을 그대로 둔다.
    if ai and settings.growth_ai_enabled and growth["compare_with_previous"] is not None:
        # [2026-09-22 수정] AI 피드백은 부가 기능이다.
        # 여기서 예외가 나면 예전에는 500이 나면서 그래프(trend)까지 함께 사라졌다.
        try:
            cache_key = (current_user.id, sessions[0]["id"], sessions[1]["id"])
            ai_text = generate_growth_feedback(cache_key, growth["compare_with_previous"])
            if ai_text:
                growth["feedback"] = ai_text
                growth["feedback_source"] = "ai"
        except Exception:
            logger.exception("growth AI feedback failed; keeping rule-based feedback")

    return report

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
