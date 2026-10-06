"""발표 영상 공유 게시판 API.

기능_추가_제안서.hwp "기능 1. 발표 영상 공유 게시판" 대응 라우터.
main.py에는 이미 아래 두 줄이 들어 있으므로 main.py는 수정하지 않는다.

    from app.routers import analysis, auth, history, slides, board
    app.include_router(board.router, prefix="/api/board", tags=["board"])

엔드포인트 (모두 로그인 필요)
- POST   /api/board/upload-video           영상 -> Supabase Storage 업로드, 저장 경로 반환
- POST   /api/board                        게시글 등록 (분석 결과 스냅샷 자동 첨부)
- GET    /api/board                        목록/검색 (q=제목, topic, tag, sort=latest|score)
- GET    /api/board/mine                   내 게시글 (비공개 포함)
- GET    /api/board/{post_id}              상세 (영상 URL + 분석 스냅샷 + 댓글)
- DELETE /api/board/{post_id}              게시글 삭제 (작성자만)
- POST   /api/board/{post_id}/comments     댓글 등록
- DELETE /api/board/{post_id}/comments/{comment_id}   댓글 삭제 (댓글 작성자 또는 글 작성자)
- GET    /api/board/{post_id}/recommendations         같은 주제의 AI 점수 상위 사례 추천
"""
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.database import get_supabase
from app.middleware.auth import CurrentUser, get_current_user
from app.services.board_schema import build_board_post

router = APIRouter()

# 브라우저 <video>로 바로 재생 가능한 형식만 허용한다.
VIDEO_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}
SIGNED_URL_TTL_SEC = 60 * 60  # 영상 재생용 임시 URL 유효 시간(1시간)

# 목록 응답에는 무거운 snapshot / video_url을 넣지 않는다.
_LIST_COLS = "id,user_id,author_name,title,topic,tags,score_total,is_public,created_at"


# ----------------------------------------------------------------------------- #
# 요청 모델
# ----------------------------------------------------------------------------- #
class CreatePostRequest(BaseModel):
    analysis_result_id: str
    title: str = Field(min_length=1, max_length=100)
    topic: str = Field(min_length=1, max_length=50)
    tags: list[str] = Field(default_factory=list)
    video_storage_path: str  # /upload-video 응답의 video_storage_path
    is_public: bool = True   # 개인정보 노출 리스크 대응: 공개 여부를 작성자가 선택

    @field_validator("title", "topic")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("빈 값은 사용할 수 없습니다.")
        return v

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, v: list[str]) -> list[str]:
        cleaned: list[str] = []
        for tag in v:
            tag = tag.strip().lstrip("#").strip()
            if tag and len(tag) <= 20 and tag not in cleaned:
                cleaned.append(tag)
        return cleaned[:10]


class CommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("댓글 내용을 입력해 주세요.")
        return v


# ----------------------------------------------------------------------------- #
# 내부 헬퍼
# ----------------------------------------------------------------------------- #
def _author_name(user: CurrentUser) -> str:
    # 이메일은 노출하지 않는다.
    return user.name or "익명"


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _signed_url(storage_path: str | None) -> str | None:
    """비공개 버킷의 영상을 재생할 수 있는 임시 URL을 만든다."""
    if not storage_path:
        return None
    try:
        res = get_supabase().storage.from_(settings.board_video_bucket).create_signed_url(
            storage_path, SIGNED_URL_TTL_SEC
        )
    except Exception:
        return None

    url = (res.get("signedURL") or res.get("signedUrl")) if isinstance(res, dict) else None
    if url and not url.startswith("http"):
        url = settings.supabase_url.rstrip("/") + "/storage/v1" + (url if url.startswith("/") else f"/{url}")
    return url


def _upload_to_storage(local_path: Path, storage_path: str, content_type: str) -> None:
    with local_path.open("rb") as f:
        get_supabase().storage.from_(settings.board_video_bucket).upload(
            storage_path, f, {"content-type": content_type}
        )


def _get_post_or_404(post_id: str, current_user: CurrentUser) -> dict:
    try:
        res = get_supabase().table("board_posts").select("*").eq("id", post_id).limit(1).execute()
    except Exception as e:
        raise HTTPException(500, f"게시글 조회 실패: {e}")

    if not res.data:
        raise HTTPException(404, "게시글을 찾을 수 없습니다.")

    post = res.data[0]
    # 비공개 글은 작성자만 볼 수 있다. 존재 여부도 숨기려고 403이 아닌 404를 쓴다.
    if not post.get("is_public") and post.get("user_id") != current_user.id:
        raise HTTPException(404, "게시글을 찾을 수 없습니다.")
    return post


# ----------------------------------------------------------------------------- #
# 영상 업로드 (Supabase Storage)
# ----------------------------------------------------------------------------- #
@router.post("/upload-video")
async def upload_video(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    """게시글에 첨부할 영상을 Supabase Storage에 올리고 경로를 돌려준다.

    분석 API는 분석이 끝나면 서버의 임시 영상을 지우므로, 게시하려면 영상을 다시 올려야 한다.
    """
    suffix = Path(file.filename or "").suffix.lower()
    content_type = VIDEO_CONTENT_TYPES.get(suffix)
    if content_type is None:
        raise HTTPException(400, "게시판 영상은 MP4, WebM, MOV 형식만 올릴 수 있습니다.")

    max_bytes = settings.board_max_video_mb * 1024 * 1024
    tmp_path = Path(settings.upload_dir) / f"board_{uuid.uuid4().hex}{suffix}"
    storage_path = f"board/{current_user.id}/{uuid.uuid4().hex}{suffix}"

    try:
        size = 0
        with tmp_path.open("wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(413, f"영상은 {settings.board_max_video_mb}MB 이하만 올릴 수 있습니다.")
                f.write(chunk)

        try:
            await run_in_threadpool(_upload_to_storage, tmp_path, storage_path, content_type)
        except Exception as e:
            raise HTTPException(500, f"영상 업로드 실패: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"video_storage_path": storage_path, "video_url": _signed_url(storage_path)}


# ----------------------------------------------------------------------------- #
# 게시글
# ----------------------------------------------------------------------------- #
@router.post("", status_code=201)
def create_post(body: CreatePostRequest, current_user: CurrentUser = Depends(get_current_user)):
    """분석 완료된 발표 영상을 게시판에 등록한다. (사용자 시나리오 2~3)"""
    # 다른 사용자의 영상 경로를 끌어다 쓰지 못하게 막는다.
    if not body.video_storage_path.startswith(f"board/{current_user.id}/"):
        raise HTTPException(400, "본인이 업로드한 영상만 게시할 수 있습니다.")

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

    # build_board_post()가 "계획서에 적힌 JSON 조각을 출력하는 코드"에 해당한다.
    payload = build_board_post(
        post_id=uuid.uuid4().hex,
        user_id=current_user.id,
        author_name=_author_name(current_user),
        title=body.title,
        topic=body.topic,
        tags=body.tags,
        video_storage_path=body.video_storage_path,
        is_public=body.is_public,
        analysis_result=res.data[0],
    )

    try:
        insert_res = get_supabase().table("board_posts").insert(payload).execute()
    except Exception as e:
        raise HTTPException(500, f"게시글 등록 실패: {e}")

    return insert_res.data[0]


@router.get("")
def list_posts(
    q: str | None = Query(None, description="제목 검색어"),
    topic: str | None = Query(None, description="발표 주제로 필터링"),
    tag: str | None = Query(None, description="태그로 필터링"),
    sort: Literal["latest", "score"] = Query("latest", description="latest=최신순, score=AI 점수 높은 순"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
):
    """공개 게시글 목록/검색. (사용자 시나리오 4: 제목·주제·태그 검색)"""
    offset = (page - 1) * limit
    try:
        query = get_supabase().table("board_posts").select(_LIST_COLS, count="exact").eq("is_public", True)
        if q and q.strip():
            query = query.ilike("title", f"%{_escape_like(q.strip())}%")
        if topic:
            query = query.eq("topic", topic)
        if tag:
            query = query.contains("tags", [tag.lstrip("#")])  # tags: text[] 컬럼, 배열 포함 검색

        if sort == "score":
            query = query.order("score_total", desc=True).order("created_at", desc=True)
        else:
            query = query.order("created_at", desc=True)

        res = query.range(offset, offset + limit - 1).execute()
    except Exception as e:
        raise HTTPException(500, f"게시글 목록 조회 실패: {e}")

    return {"items": res.data, "page": page, "limit": limit, "total": getattr(res, "count", None)}


@router.get("/mine")
def list_my_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
):
    """내가 올린 게시글 (비공개 포함). ※ '/{post_id}'보다 위에 있어야 한다."""
    offset = (page - 1) * limit
    try:
        res = (
            get_supabase()
            .table("board_posts")
            .select(_LIST_COLS)
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"내 게시글 조회 실패: {e}")
    return {"items": res.data, "page": page, "limit": limit}


@router.get("/{post_id}")
def get_post(post_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """게시글 상세 (영상 + AI 분석 결과 스냅샷 + 댓글). (사용자 시나리오 5~6)"""
    post = _get_post_or_404(post_id, current_user)

    try:
        comments_res = (
            get_supabase()
            .table("board_comments")
            .select("id,user_id,author_name,content,created_at")
            .eq("post_id", post_id)
            .order("created_at")
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"댓글 조회 실패: {e}")

    post["comments"] = comments_res.data
    post["video_signed_url"] = _signed_url(post.get("video_url"))
    post["is_owner"] = post.get("user_id") == current_user.id
    return post


@router.delete("/{post_id}")
def delete_post(post_id: str, current_user: CurrentUser = Depends(get_current_user)):
    post = _get_post_or_404(post_id, current_user)
    if post.get("user_id") != current_user.id:
        raise HTTPException(403, "본인의 게시글만 삭제할 수 있습니다.")

    try:
        get_supabase().table("board_posts").delete().eq("id", post_id).execute()  # 댓글은 FK cascade
    except Exception as e:
        raise HTTPException(500, f"게시글 삭제 실패: {e}")

    # 영상 파일 삭제는 실패해도 글 삭제 결과에는 영향을 주지 않는다.
    try:
        get_supabase().storage.from_(settings.board_video_bucket).remove([post["video_url"]])
    except Exception:
        pass
    return {"ok": True}


# ----------------------------------------------------------------------------- #
# 댓글
# ----------------------------------------------------------------------------- #
@router.post("/{post_id}/comments", status_code=201)
def add_comment(post_id: str, body: CommentRequest, current_user: CurrentUser = Depends(get_current_user)):
    """댓글을 통한 피드백 (사용자 시나리오 6)."""
    _get_post_or_404(post_id, current_user)  # 존재/공개 여부 확인

    payload = {
        "id": uuid.uuid4().hex,
        "post_id": post_id,
        "user_id": current_user.id,
        "author_name": _author_name(current_user),
        "content": body.content,
    }
    try:
        res = get_supabase().table("board_comments").insert(payload).execute()
    except Exception as e:
        raise HTTPException(500, f"댓글 등록 실패: {e}")
    return res.data[0]


@router.delete("/{post_id}/comments/{comment_id}")
def delete_comment(post_id: str, comment_id: str, current_user: CurrentUser = Depends(get_current_user)):
    post = _get_post_or_404(post_id, current_user)
    try:
        res = (
            get_supabase()
            .table("board_comments")
            .select("id,user_id")
            .eq("id", comment_id)
            .eq("post_id", post_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"댓글 조회 실패: {e}")

    if not res.data:
        raise HTTPException(404, "댓글을 찾을 수 없습니다.")
    if current_user.id not in (res.data[0]["user_id"], post.get("user_id")):
        raise HTTPException(403, "댓글을 삭제할 권한이 없습니다.")

    try:
        get_supabase().table("board_comments").delete().eq("id", comment_id).execute()
    except Exception as e:
        raise HTTPException(500, f"댓글 삭제 실패: {e}")
    return {"ok": True}


# ----------------------------------------------------------------------------- #
# 추천 (목표 5: AI 점수가 높은 발표 사례 추천)
# ----------------------------------------------------------------------------- #
@router.get("/{post_id}/recommendations")
def recommend_similar(
    post_id: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: CurrentUser = Depends(get_current_user),
):
    """같은 주제의 공개 게시글을 AI 점수(score_total) 높은 순으로 추천한다.

    같은 주제 글이 limit보다 적으면 전체 공개 글의 점수 상위로 채운다.
    임베딩 기반 유사도 추천은 제안서의 '확장 기능(범위 외)'이라 규칙 기반으로 둔다.
    """
    post = _get_post_or_404(post_id, current_user)

    def _top(extra_topic: str | None, size: int) -> list[dict]:
        query = (
            get_supabase()
            .table("board_posts")
            .select(_LIST_COLS)
            .eq("is_public", True)
            .neq("id", post_id)
        )
        if extra_topic:
            query = query.eq("topic", extra_topic)
        return query.order("score_total", desc=True).limit(size).execute().data

    try:
        items = _top(post["topic"], limit)
        if len(items) < limit:
            seen = {row["id"] for row in items}
            filler = [row for row in _top(None, limit + len(items)) if row["id"] not in seen]
            items += filler[: limit - len(items)]
    except Exception as e:
        raise HTTPException(500, f"추천 조회 실패: {e}")

    return {"items": items}
