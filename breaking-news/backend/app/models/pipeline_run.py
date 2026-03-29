from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class PipelineRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default="queued")
    current_stage: str = Field(default="queued")
    progress_percent: int = Field(default=0)
    message: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = Field(default=None)