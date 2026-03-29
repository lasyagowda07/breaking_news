from typing import Optional
from sqlalchemy import Column
from sqlmodel import SQLModel, Field
from pgvector.sqlalchemy import Vector


class OutletMonthCentroid(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    media_name: str = Field(index=True)
    year_month: str = Field(index=True)
    num_headlines: int

    centroid: list = Field(sa_column=Column(Vector(384)))