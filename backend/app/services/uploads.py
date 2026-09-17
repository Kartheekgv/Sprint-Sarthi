import hashlib
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".md", ".csv"}
ALLOWED_MEDIA_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/csv",
}


def safe_filename(filename: str) -> str:
    leaf = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", leaf).strip("._")
    return cleaned[:180] or "document"


async def save_upload(file: UploadFile, upload_dir: Path, max_bytes: int) -> tuple[str, int, str]:
    original = safe_filename(file.filename or "document")
    extension = Path(original).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF, DOCX, XLSX, TXT, Markdown, and CSV files are allowed")

    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4()}{extension}"
    destination = (upload_dir / stored_name).resolve()
    if upload_dir.resolve() not in destination.parents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid filename")

    digest = hashlib.sha256()
    size = 0
    try:
        with destination.open("xb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds upload limit")
                digest.update(chunk)
                output.write(chunk)
        if size == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return stored_name, size, digest.hexdigest()
