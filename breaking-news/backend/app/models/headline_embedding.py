from typing import Optional
from sqlalchemy import Column
from sqlmodel import SQLModel, Field
from pgvector.sqlalchemy import Vector


class HeadlineEmbedding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    headline_id: int = Field(index=True)
    embedding: list = Field(sa_column=Column(Vector(384)))