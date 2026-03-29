from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    filename: str
    content_type: Optional[str] = None
    size_bytes: int
    message: str
    pipeline_run_id: int