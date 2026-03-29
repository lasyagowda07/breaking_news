from typing import Optional
from sqlmodel import SQLModel, Field


class MonthlyMetric(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    year_month: str = Field(index=True)
    headline_count_before_anchor: int
    headline_count_after_anchor: int
    num_outlets: int
    polarization_score: float
    mean_sentiment: float