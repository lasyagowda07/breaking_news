from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func

from app.db.database import get_session
from app.models.headline import Headline
from app.models.monthly_metric import MonthlyMetric

router = APIRouter(prefix="", tags=["explore"])


@router.get("/months/{year_month}/summary")
def get_month_summary(year_month: str, session: Session = Depends(get_session)):
    metric_stmt = select(MonthlyMetric).where(MonthlyMetric.year_month == year_month)
    metric = session.exec(metric_stmt).first()

    if not metric:
        raise HTTPException(status_code=404, detail="Month not found")

    top_outlets_stmt = (
        select(
            Headline.media_name,
            func.count(Headline.id).label("headline_count"),
        )
        .where(Headline.year_month == year_month)
        .group_by(Headline.media_name)
        .order_by(func.count(Headline.id).desc())
        .limit(5)
    )
    top_outlets_rows = session.exec(top_outlets_stmt).all()

    sentiment_stmt = (
        select(
            Headline.sentiment_label,
            func.count(Headline.id).label("count"),
        )
        .where(Headline.year_month == year_month)
        .group_by(Headline.sentiment_label)
    )
    sentiment_rows = session.exec(sentiment_stmt).all()

    sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0}
    for row in sentiment_rows:
        if row.sentiment_label in sentiment_distribution:
            sentiment_distribution[row.sentiment_label] = row.count

    return {
        "year_month": metric.year_month,
        "headline_count_before_anchor": metric.headline_count_before_anchor,
        "headline_count_after_anchor": metric.headline_count_after_anchor,
        "num_outlets": metric.num_outlets,
        "polarization_score": metric.polarization_score,
        "mean_sentiment": metric.mean_sentiment,
        "top_outlets": [
            {
                "media_name": row.media_name,
                "headline_count": row.headline_count,
            }
            for row in top_outlets_rows
        ],
        "sentiment_distribution": sentiment_distribution,
    }


@router.get("/months/{year_month}/top-outlets")
def get_month_top_outlets(
    year_month: str,
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    stmt = (
        select(
            Headline.media_name,
            func.count(Headline.id).label("headline_count"),
            func.avg(Headline.sentiment).label("mean_sentiment"),
        )
        .where(Headline.year_month == year_month)
        .group_by(Headline.media_name)
        .order_by(func.count(Headline.id).desc())
        .limit(limit)
    )
    rows = session.exec(stmt).all()

    if not rows:
        raise HTTPException(status_code=404, detail="No outlets found for this month")

    return [
        {
            "media_name": row.media_name,
            "headline_count": row.headline_count,
            "mean_sentiment": float(row.mean_sentiment) if row.mean_sentiment is not None else None,
        }
        for row in rows
    ]


@router.get("/outlets/{media_name}/headlines")
def get_outlet_headlines(
    media_name: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    year_month: str = Query(default=None),
    sentiment_label: str = Query(default=None),
    session: Session = Depends(get_session),
):
    stmt = select(Headline).where(Headline.media_name == media_name)

    if year_month:
        stmt = stmt.where(Headline.year_month == year_month)

    if sentiment_label:
        stmt = stmt.where(Headline.sentiment_label == sentiment_label)

    stmt = stmt.offset(offset).limit(limit)
    rows = session.exec(stmt).all()

    if not rows:
        raise HTTPException(status_code=404, detail="No headlines found for this outlet")

    return [
        {
            "id": row.id,
            "publish_date": row.publish_date,
            "title": row.title,
            "url": row.url,
            "year_month": row.year_month,
            "anchor_similarity": row.anchor_similarity,
            "sentiment": row.sentiment,
            "sentiment_label": row.sentiment_label,
        }
        for row in rows
    ]


@router.get("/search/headlines")
def search_headlines(
    keyword: str = Query(..., min_length=2),
    limit: int = Query(default=50, ge=1, le=200),
    year_month: str = Query(default=None),
    outlet: str = Query(default=None),
    sentiment_label: str = Query(default=None),
    session: Session = Depends(get_session),
):
    stmt = select(Headline).where(Headline.title.ilike(f"%{keyword}%"))

    if year_month:
        stmt = stmt.where(Headline.year_month == year_month)

    if outlet:
        stmt = stmt.where(Headline.media_name == outlet)

    if sentiment_label:
        stmt = stmt.where(Headline.sentiment_label == sentiment_label)

    stmt = stmt.limit(limit)
    rows = session.exec(stmt).all()

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


@router.get("/dashboard/overview")
def get_dashboard_overview(session: Session = Depends(get_session)):
    total_uploads_stmt = select(func.count()).select_from(Headline)
    total_headlines = session.exec(total_uploads_stmt).one()

    total_outlets_stmt = select(func.count(func.distinct(Headline.media_name)))
    total_outlets = session.exec(total_outlets_stmt).one()

    total_months_stmt = select(func.count(func.distinct(MonthlyMetric.year_month)))
    total_months = session.exec(total_months_stmt).one()

    latest_month_stmt = (
        select(MonthlyMetric)
        .order_by(MonthlyMetric.year_month.desc())
        .limit(1)
    )
    latest_month = session.exec(latest_month_stmt).first()

    highest_pol_stmt = (
        select(MonthlyMetric)
        .order_by(MonthlyMetric.polarization_score.desc())
        .limit(1)
    )
    highest_pol = session.exec(highest_pol_stmt).first()

    lowest_pol_stmt = (
        select(MonthlyMetric)
        .order_by(MonthlyMetric.polarization_score.asc())
        .limit(1)
    )
    lowest_pol = session.exec(lowest_pol_stmt).first()

    return {
        "total_headlines": total_headlines,
        "total_outlets": total_outlets,
        "total_months": total_months,
        "latest_month": {
            "year_month": latest_month.year_month,
            "headline_count_after_anchor": latest_month.headline_count_after_anchor,
            "num_outlets": latest_month.num_outlets,
            "polarization_score": latest_month.polarization_score,
            "mean_sentiment": latest_month.mean_sentiment,
        } if latest_month else None,
        "highest_polarization_month": {
            "year_month": highest_pol.year_month,
            "polarization_score": highest_pol.polarization_score,
        } if highest_pol else None,
        "lowest_polarization_month": {
            "year_month": lowest_pol.year_month,
            "polarization_score": lowest_pol.polarization_score,
        } if lowest_pol else None,
    }


@router.get("/outlets/{media_name}/summary")
def get_outlet_summary(media_name: str, session: Session = Depends(get_session)):
    overview_stmt = (
        select(
            func.count(Headline.id).label("headline_count"),
            func.count(func.distinct(Headline.year_month)).label("months_active"),
            func.min(Headline.year_month).label("first_month"),
            func.max(Headline.year_month).label("last_month"),
            func.avg(Headline.sentiment).label("mean_sentiment"),
            func.avg(Headline.anchor_similarity).label("mean_anchor_similarity"),
        )
        .where(Headline.media_name == media_name)
    )
    overview = session.exec(overview_stmt).first()

    if not overview or overview.headline_count == 0:
        raise HTTPException(status_code=404, detail="Outlet not found")

    sentiment_stmt = (
        select(
            Headline.sentiment_label,
            func.count(Headline.id).label("count"),
        )
        .where(Headline.media_name == media_name)
        .group_by(Headline.sentiment_label)
    )
    sentiment_rows = session.exec(sentiment_stmt).all()

    sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0}
    for row in sentiment_rows:
        if row.sentiment_label in sentiment_distribution:
            sentiment_distribution[row.sentiment_label] = row.count

    top_months_stmt = (
        select(
            Headline.year_month,
            func.count(Headline.id).label("headline_count"),
        )
        .where(Headline.media_name == media_name)
        .group_by(Headline.year_month)
        .order_by(func.count(Headline.id).desc())
        .limit(5)
    )
    top_months = session.exec(top_months_stmt).all()

    return {
        "media_name": media_name,
        "headline_count": overview.headline_count,
        "months_active": overview.months_active,
        "first_month": overview.first_month,
        "last_month": overview.last_month,
        "mean_sentiment": float(overview.mean_sentiment) if overview.mean_sentiment is not None else None,
        "mean_anchor_similarity": float(overview.mean_anchor_similarity) if overview.mean_anchor_similarity is not None else None,
        "sentiment_distribution": sentiment_distribution,
        "top_months": [
            {
                "year_month": row.year_month,
                "headline_count": row.headline_count,
            }
            for row in top_months
        ],
    }


@router.get("/months/compare")
def compare_months(
    month_a: str = Query(...),
    month_b: str = Query(...),
    session: Session = Depends(get_session),
):
    stmt = select(MonthlyMetric).where(MonthlyMetric.year_month.in_([month_a, month_b]))
    rows = session.exec(stmt).all()

    if len(rows) != 2:
        raise HTTPException(status_code=404, detail="One or both months not found")

    metrics = {row.year_month: row for row in rows}
    a = metrics.get(month_a)
    b = metrics.get(month_b)

    top_a_stmt = (
        select(
            Headline.media_name,
            func.count(Headline.id).label("headline_count"),
        )
        .where(Headline.year_month == month_a)
        .group_by(Headline.media_name)
        .order_by(func.count(Headline.id).desc())
        .limit(5)
    )
    top_b_stmt = (
        select(
            Headline.media_name,
            func.count(Headline.id).label("headline_count"),
        )
        .where(Headline.year_month == month_b)
        .group_by(Headline.media_name)
        .order_by(func.count(Headline.id).desc())
        .limit(5)
    )

    top_a = session.exec(top_a_stmt).all()
    top_b = session.exec(top_b_stmt).all()

    return {
        "month_a": {
            "year_month": a.year_month,
            "headline_count_before_anchor": a.headline_count_before_anchor,
            "headline_count_after_anchor": a.headline_count_after_anchor,
            "num_outlets": a.num_outlets,
            "polarization_score": a.polarization_score,
            "mean_sentiment": a.mean_sentiment,
            "top_outlets": [
                {"media_name": row.media_name, "headline_count": row.headline_count}
                for row in top_a
            ],
        },
        "month_b": {
            "year_month": b.year_month,
            "headline_count_before_anchor": b.headline_count_before_anchor,
            "headline_count_after_anchor": b.headline_count_after_anchor,
            "num_outlets": b.num_outlets,
            "polarization_score": b.polarization_score,
            "mean_sentiment": b.mean_sentiment,
            "top_outlets": [
                {"media_name": row.media_name, "headline_count": row.headline_count}
                for row in top_b
            ],
        },
        "delta": {
            "headline_count_after_anchor": a.headline_count_after_anchor - b.headline_count_after_anchor,
            "num_outlets": a.num_outlets - b.num_outlets,
            "polarization_score": a.polarization_score - b.polarization_score,
            "mean_sentiment": a.mean_sentiment - b.mean_sentiment,
        },
    }