import subprocess
import shutil
import uuid
from pathlib import Path

import fitz  # PyMuPDF

from app.core.config import settings

LIBREOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"

def _pdf_to_images(pdf_path: Path, out_dir: Path) -> list[str]:
    """PDF 각 페이지를 PNG로 변환. URL 경로 목록 반환."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    urls = []
    for i, page in enumerate(doc):
        mat = fitz.Matrix(2.0, 2.0)  # 2x 해상도
        pix = page.get_pixmap(matrix=mat)
        img_name = f"slide_{i + 1:03d}.png"
        pix.save(str(out_dir / img_name))
        urls.append(f"/static/slides/{out_dir.name}/{img_name}")
    doc.close()
    return urls


def _pptx_to_pdf(pptx_path: Path, out_dir: Path) -> Path:
    """LibreOffice headless로 PPTX → PDF 변환."""
    result = subprocess.run(
        [
            LIBREOFFICE_PATH,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(pptx_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice 변환 실패: {result.stderr}")
    pdf_name = pptx_path.stem + ".pdf"
    return out_dir / pdf_name


def convert_to_slides(file_path: Path, filename: str) -> tuple[str, list[str]]:
    """
    업로드된 PPTX 또는 PDF를 슬라이드 이미지로 변환.
    Returns (session_id, [image_url, ...])
    """
    session_id = uuid.uuid4().hex
    slides_dir = Path(settings.static_dir) / "slides" / session_id
    slides_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        urls = _pdf_to_images(file_path, slides_dir)
    elif suffix in (".pptx", ".ppt"):
        tmp_dir = Path(settings.upload_dir) / session_id
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            pdf_path = _pptx_to_pdf(file_path, tmp_dir)
            urls = _pdf_to_images(pdf_path, slides_dir)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {suffix}")

    return session_id, urls


def delete_session(session_id: str) -> None:
    slides_dir = Path(settings.static_dir) / "slides" / session_id
    shutil.rmtree(slides_dir, ignore_errors=True)
