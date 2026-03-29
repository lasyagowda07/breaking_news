from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Upload(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    file_path: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    status: str = "uploaded"
    validation_message: Optional[str] = None