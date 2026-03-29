from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from app.db.database import get_session
from app.models.headline import Headline

router = APIRouter(prefix="/outlets", tags=["outlets"])


@router.get("")
def list_outlets(session: Session = Depends(get_session)):
    statement = (
        select(
            Headline.media_name,
            func.count(Headline.id).label("headline_count"),
            func.min(Headline.year_month).label("first_month"),
            func.max(Headline.year_month).label("last_month"),
            func.avg(Headline.sentiment).label("mean_sentiment"),
        )
        .group_by(Headline.media_name)
        .order_by(func.count(Headline.id).desc())
    )

    rows = session.exec(statement).all()

    return [
        {
            "media_name": row.media_name,
            "headline_count": row.headline_count,
            "first_month": row.first_month,
            "last_month": row.last_month,
            "mean_sentiment": float(row.mean_sentiment) if row.mean_sentiment is not None else None,
        }
        for row in rows
    ]


@router.get("/{media_name}")
def get_outlet_overview(media_name: str, session: Session = Depends(get_session)):
    statement = (
        select(
            func.count(Headline.id).label("headline_count"),
            func.min(Headline.year_month).label("first_month"),
            func.max(Headline.year_month).label("last_month"),
            func.avg(Headline.sentiment).label("mean_sentiment"),
        )
        .where(Headline.media_name == media_name)
    )

    row = session.exec(statement).first()

    if not row or row.headline_count == 0:
        raise HTTPException(status_code=404, detail="Outlet not found")

    distinct_months_statement = (
        select(func.count(func.distinct(Headline.year_month)))
        .where(Headline.media_name == media_name)
    )
    months_active = session.exec(distinct_months_statement).one()

    return {
        "media_name": media_name,
        "headline_count": row.headline_count,
        "months_active": months_active,
        "first_month": row.first_month,
        "last_month": row.last_month,
        "mean_sentiment": float(row.mean_sentiment) if row.mean_sentiment is not None else None,
    }


@router.get("/{media_name}/timeline")
def get_outlet_timeline(media_name: str, session: Session = Depends(get_session)):
    statement = (
        select(
            Headline.year_month,
            func.count(Headline.id).label("headline_count"),
            func.avg(Headline.sentiment).label("mean_sentiment"),
        )
        .where(Headline.media_name == media_name)
        .group_by(Headline.year_month)
        .order_by(Headline.year_month)
    )

    rows = session.exec(statement).all()

    if not rows:
        raise HTTPException(status_code=404, detail="Outlet not found")

    return [
        {
            "year_month": row.year_month,
            "headline_count": row.headline_count,
            "mean_sentiment": float(row.mean_sentiment) if row.mean_sentiment is not None else None,
        }
        for row in rows
    ]