import os
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Header, BackgroundTasks, Depends
from jose import jwt, JWTError
from sqlmodel import Session, select

from app.core.config import SECRET_KEY, UPLOAD_DIR
from app.db.database import get_session
from app.models.upload import Upload
from app.models.pipeline_run import PipelineRun
from app.schemas.upload import UploadResponse
from app.services.pipeline_service import process_all_uploads

ALGORITHM = "HS256"

router = APIRouter(prefix="/uploads", tags=["uploads"])


def verify_token(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/csv", response_model=UploadResponse)
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
):
    verify_token(authorization)

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    upload_record = Upload(
        filename=file.filename,
        file_path=file_path,
        row_count=None,
        column_count=None,
        status="uploaded",
        validation_message="File uploaded and queued for processing",
    )
    session.add(upload_record)

    pipeline_run = PipelineRun(
        status="queued",
        current_stage="queued",
        progress_percent=0,
        message="Upload received. Waiting to start pipeline.",
    )
    session.add(pipeline_run)
    session.commit()
    session.refresh(pipeline_run)

    background_tasks.add_task(process_all_uploads, pipeline_run.id)

    return UploadResponse(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(contents),
        message="CSV uploaded and pipeline started",
        pipeline_run_id=pipeline_run.id,
    )


@router.get("/{upload_id}")
def get_upload(
    upload_id: int,
    session: Session = Depends(get_session),
):
    upload = session.get(Upload, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    return {
        "id": upload.id,
        "filename": upload.filename,
        "file_path": upload.file_path,
        "uploaded_at": upload.uploaded_at,
        "row_count": upload.row_count,
        "column_count": upload.column_count,
        "status": upload.status,
        "validation_message": upload.validation_message,
    }


@router.delete("/{upload_id}")
def delete_upload(
    upload_id: int,
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
):
    verify_token(authorization)

    upload = session.get(Upload, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    if upload.file_path and os.path.exists(upload.file_path):
        os.remove(upload.file_path)

    session.delete(upload)
    session.commit()

    return {"message": "Upload deleted successfully", "upload_id": upload_id}


@router.post("/rebuild")
def rebuild_from_uploads(
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
):
    verify_token(authorization)

    pipeline_run = PipelineRun(
        status="queued",
        current_stage="queued",
        progress_percent=0,
        message="Manual rebuild requested.",
    )
    session.add(pipeline_run)
    session.commit()
    session.refresh(pipeline_run)

    background_tasks.add_task(process_all_uploads, pipeline_run.id)

    return {
        "message": "Rebuild started",
        "pipeline_run_id": pipeline_run.id,
    }