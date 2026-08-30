"""[신규 추가 파일] 발표 영상 공유 게시판 API.

기능_추가_제안서.hwp "기능 1. 발표 영상 공유 게시판" 대응 라우터.
main.py에 아래처럼 등록해야 동작한다 (main.py 수정 부분 참고):

    from app.routers import analysis, auth, history, slides, board
    app.include_router(board.router, prefix="/api/board", tags=["board"])
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import get_supabase
from app.middleware.auth import CurrentUser, get_current_user
from app.services.board_schema import build_board_post

router = APIRouter()

_POST_LIST_COLS = "id,user_id,title,topic,tags,video_url,snapshot,created_at"


class CreatePostRequest(BaseModel):
    analysis_result_id: str
    title: str = Field(min_length=1, max_length=100)
    topic: str = Field(min_length=1, max_length=50)
    tags: list[str] = Field(default_factory=list)
    video_storage_path: str  # Supabase Storage 업로드 후 받은 경로 (예: sessions/xxx/video.mp4)


class CommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


@router.post("", status_code=201)
def create_post(body: CreatePostRequest, current_user: CurrentUser = Depends(get_current_user)):
    """분석 완료된 발표 영상을 게시판에 등록한다. (사용자 시나리오 2~3)"""
    try:
        res = (
            get_supabase()
            .table("analysis_results")
            .select("*")
            .eq("id", body.analysis_result_id)
            .eq("user_id", current_user.id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"분석 결과 조회 실패: {e}")

    if not res.data:
        raise HTTPException(404, "본인의 분석 결과만 게시할 수 있습니다.")

    analysis_result = res.data[0]

    # build_board_post()가 "계획서에 적힌 JSON 조각을 출력하는 코드"에 해당한다.
    payload = build_board_post(
        post_id=uuid.uuid4().hex,
        user_id=current_user.id,
        title=body.title,
        topic=body.topic,
        tags=body.tags,
        video_storage_path=body.video_storage_path,
        analysis_result=analysis_result,
    )

    try:
        insert_res = get_supabase().table("board_posts").insert(payload).execute()
    except Exception as e:
        raise HTTPException(500, f"게시글 등록 실패: {e}")

    return insert_res.data[0]


@router.get("")
def list_posts(
    topic: str | None = Query(None, description="발표 주제로 필터링"),
    tag: str | None = Query(None, description="태그로 필터링"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """게시글 목록/검색. (사용자 시나리오 4: 주제/태그 검색)"""
    offset = (page - 1) * limit
    try:
        q = (
            get_supabase()
            .table("board_posts")
            .select(_POST_LIST_COLS)
            .order("created_at", desc=True)
        )
        if topic:
            q = q.eq("topic", topic)
        if tag:
            q = q.contains("tags", [tag])  # tags: text[] 컬럼, 배열 포함 검색
        res = q.range(offset, offset + limit - 1).execute()
        return {"items": res.data, "page": page, "limit": limit}
    except Exception as e:
        raise HTTPException(500, f"게시글 목록 조회 실패: {e}")


@router.get("/{post_id}")
def get_post(post_id: str):
    """게시글 상세 (영상 + AI 분석 결과 스냅샷 + 댓글). (사용자 시나리오 5~6)"""
    try:
        post_res = get_supabase().table("board_posts").select("*").eq("id", post_id).execute()
        comments_res = (
            get_supabase()
            .table("board_comments")
            .select("id,user_id,content,created_at")
            .eq("post_id", post_id)
            .order("created_at")
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"게시글 조회 실패: {e}")

    if not post_res.data:
        raise HTTPException(404, "게시글을 찾을 수 없습니다.")

    post = post_res.data[0]
    post["comments"] = comments_res.data
    return post


@router.post("/{post_id}/comments", status_code=201)
def add_comment(post_id: str, body: CommentRequest, current_user: CurrentUser = Depends(get_current_user)):
    """댓글을 통한 피드백 (사용자 시나리오 6)."""
    payload = {
        "id": uuid.uuid4().hex,
        "post_id": post_id,
        "user_id": current_user.id,
        "content": body.content,
    }
    try:
        res = get_supabase().table("board_comments").insert(payload).execute()
    except Exception as e:
        raise HTTPException(500, f"댓글 등록 실패: {e}")
    return res.data[0]


@router.get("/{post_id}/recommendations")
def recommend_similar(post_id: str, limit: int = Query(5, ge=1, le=20)):
    """AI 점수가 높은 유사 발표 사례 추천 (목표 5).

    1~2주차 범위에서는 같은 topic + score_total 상위 게시글을 단순 정렬해
    돌려주는 규칙 기반 스텁이다. 임베딩 기반 유사도 추천은 확장 기능(범위 외)으로
    제안서에 명시되어 있어 이후 단계에서 교체한다.
    """
    try:
        target = get_supabase().table("board_posts").select("topic").eq("id", post_id).execute()
        if not target.data:
            raise HTTPException(404, "게시글을 찾을 수 없습니다.")
        topic = target.data[0]["topic"]

        res = (
            get_supabase()
            .table("board_posts")
            .select(_POST_LIST_COLS)
            .eq("topic", topic)
            .neq("id", post_id)
            .execute()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"추천 조회 실패: {e}")

    def _score(row):
        return ((row.get("snapshot") or {}).get("board_snapshot", {}).get("scores", {}) or {}).get("total") or 0

    ranked = sorted(res.data, key=_score, reverse=True)[:limit]
    return {"items": ranked}
