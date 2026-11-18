import logging
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.middleware.auth import CurrentUser, get_current_user
from app.services.slide_converter import convert_to_slides, delete_session

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt"}
MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/upload")
async def upload_slides(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"지원 형식: PDF, PPTX. 받은 형식: {suffix}")

    tmp_path = Path(settings.upload_dir) / f"{uuid.uuid4().hex}{suffix}"
    try:
        with tmp_path.open("wb") as f:
            size = 0
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, "파일 크기 초과")
                f.write(chunk)

        session_id, slides = convert_to_slides(tmp_path, file.filename)
    except ValueError as e:
        # 지원하지 않는 형식처럼 사용자가 고칠 수 있는 안내만 그대로 보낸다.
        raise HTTPException(422, str(e))
    except RuntimeError:
        # LibreOffice 오류 메시지에는 서버 경로가 섞이므로 로그에만 남긴다.
        logger.exception("슬라이드 변환 실패 (user=%s)", current_user.id)
        raise HTTPException(422, "슬라이드 변환에 실패했습니다. 파일을 확인한 뒤 다시 올려 주세요.")
    finally:
        tmp_path.unlink(missing_ok=True)

    return JSONResponse({"session_id": session_id, "slides": slides, "total": len(slides)})


@router.delete("/{session_id}")
def remove_session(session_id: str, current_user: CurrentUser = Depends(get_current_user)):
    # session_id는 uuid4().hex 형식이다. 경로 조작(../)을 막기 위해 형식을 먼저 확인한다.
    if not re.fullmatch(r"[0-9a-f]{32}", session_id):
        raise HTTPException(400, "잘못된 session_id")
    delete_session(session_id)
    return {"ok": True}
