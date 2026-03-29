from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func

from app.db.database import get_session
from app.models.headline import Headline

router = APIRouter(prefix="/months", tags=["month-details"])


@router.get("/{year_month}/headlines")
def get_month_headlines(
    year_month: str,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    outlet: str = Query(default=None),
    sentiment_label: str = Query(default=None),
    session: Session = Depends(get_session),
):
    statement = select(Headline).where(Headline.year_month == year_month)

    if outlet:
        statement = statement.where(Headline.media_name == outlet)

    if sentiment_label:
        statement = statement.where(Headline.sentiment_label == sentiment_label)

    statement = statement.offset(offset).limit(limit)
    rows = session.exec(statement).all()

    return [
        {
            "id": row.id,
            "publish_date": row.publish_date,
            "media_name": row.media_name,
            "title": row.title,
            "url": row.url,
            "year_month": row.year_month,
            "anchor_similarity": row.anchor_similarity,
            "sentiment": row.sentiment,
            "sentiment_label": row.sentiment_label,
        }
        for row in rows
    ]


@router.get("/{year_month}/outlets")
def get_month_outlets(
    year_month: str,
    session: Session = Depends(get_session),
):
    statement = (
        select(
            Headline.media_name,
            func.count(Headline.id).label("headline_count"),
            func.avg(Headline.sentiment).label("mean_sentiment"),
        )
        .where(Headline.year_month == year_month)
        .group_by(Headline.media_name)
        .order_by(func.count(Headline.id).desc())
    )

    rows = session.exec(statement).all()

    return [
        {
            "media_name": row.media_name,
            "headline_count": row.headline_count,
            "mean_sentiment": float(row.mean_sentiment) if row.mean_sentiment is not None else None,
        }
        for row in rows
    ]