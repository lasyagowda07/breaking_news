from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from app.db.database import get_session
from app.models.headline import Headline

router = APIRouter(prefix="", tags=["sentiment"])


@router.get("/months/{year_month}/sentiment-distribution")
def get_month_sentiment_distribution(
    year_month: str,
    session: Session = Depends(get_session),
):
    statement = (
        select(
            Headline.sentiment_label,
            func.count(Headline.id).label("count"),
        )
        .where(Headline.year_month == year_month)
        .group_by(Headline.sentiment_label)
    )

    rows = session.exec(statement).all()

    if not rows:
        raise HTTPException(status_code=404, detail="No sentiment data found for this month")

    result = {"positive": 0, "neutral": 0, "negative": 0}

    for row in rows:
        if row.sentiment_label in result:
            result[row.sentiment_label] = row.count

    return {
        "year_month": year_month,
        "distribution": result,
    }


@router.get("/outlets/{media_name}/sentiment-distribution")
def get_outlet_sentiment_distribution(
    media_name: str,
    session: Session = Depends(get_session),
):
    statement = (
        select(
            Headline.sentiment_label,
            func.count(Headline.id).label("count"),
        )
        .where(Headline.media_name == media_name)
        .group_by(Headline.sentiment_label)
    )

    rows = session.exec(statement).all()

    if not rows:
        raise HTTPException(status_code=404, detail="No sentiment data found for this outlet")

    result = {"positive": 0, "neutral": 0, "negative": 0}

    for row in rows:
        if row.sentiment_label in result:
            result[row.sentiment_label] = row.count

    return {
        "media_name": media_name,
        "distribution": result,
    }