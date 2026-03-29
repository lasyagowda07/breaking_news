from typing import Optional
from pydantic import BaseModel


class PipelineRunResponse(BaseModel):
    id: int
    status: str
    current_stage: str
    progress_percent: int
    message: Optional[str] = None
    error_message: Optional[str] = None