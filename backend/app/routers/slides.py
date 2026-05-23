import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.slide_converter import convert_to_slides, delete_session

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt"}
MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/upload")
async def upload_slides(file: UploadFile = File(...)):
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
    except (ValueError, RuntimeError) as e:
        raise HTTPException(422, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)

    return JSONResponse({"session_id": session_id, "slides": slides, "total": len(slides)})


@router.delete("/{session_id}")
def remove_session(session_id: str):
    delete_session(session_id)
    return {"ok": True}
