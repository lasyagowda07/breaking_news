from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.database import get_session
from app.models.upload import Upload

router = APIRouter(prefix="/uploads", tags=["uploads-history"])


@router.get("")
def list_uploads(session: Session = Depends(get_session)):
    statement = select(Upload).order_by(Upload.uploaded_at.desc())
    uploads = session.exec(statement).all()

    return [
        {
            "id": upload.id,
            "filename": upload.filename,
            "file_path": upload.file_path,
            "uploaded_at": upload.uploaded_at,
            "row_count": upload.row_count,
            "column_count": upload.column_count,
            "status": upload.status,
            "validation_message": upload.validation_message,
        }
        for upload in uploads
    ]