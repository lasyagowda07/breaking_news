from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.database import get_session
from app.models.monthly_metric import MonthlyMetric

router = APIRouter(prefix="/months", tags=["months"])


@router.get("")
def list_months(session: Session = Depends(get_session)):
    statement = select(MonthlyMetric).order_by(MonthlyMetric.year_month)
    rows = session.exec(statement).all()

    return [
        {
            "year_month": row.year_month,
            "headline_count_before_anchor": row.headline_count_before_anchor,
            "headline_count_after_anchor": row.headline_count_after_anchor,
            "num_outlets": row.num_outlets,
            "polarization_score": row.polarization_score,
            "mean_sentiment": row.mean_sentiment,
        }
        for row in rows
    ]


@router.get("/{year_month}")
def get_month(year_month: str, session: Session = Depends(get_session)):
    statement = select(MonthlyMetric).where(MonthlyMetric.year_month == year_month)
    row = session.exec(statement).first()

    if not row:
        raise HTTPException(status_code=404, detail="Month not found")

    return {
        "year_month": row.year_month,
        "headline_count_before_anchor": row.headline_count_before_anchor,
        "headline_count_after_anchor": row.headline_count_after_anchor,
        "num_outlets": row.num_outlets,
        "polarization_score": row.polarization_score,
        "mean_sentiment": row.mean_sentiment,
    }