from typing import Optional
from datetime import datetime, date
from sqlmodel import SQLModel, Field


class Headline(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    publish_date: datetime
    media_name: str = Field(index=True)
    language: str = Field(index=True)
    title: str
    url: str
    date: date
    year: int = Field(index=True)
    month: int = Field(index=True)
    year_month: str = Field(index=True)

    title_clean: str
    anchor_similarity: Optional[float] = None
    sentiment: Optional[float] = None
    sentiment_label: Optional[str] = Field(default=None, index=True)