import os
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Header, BackgroundTasks, Depends
from jose import jwt, JWTError
from sqlmodel import Session

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