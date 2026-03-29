import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sklearn.metrics.pairwise import cosine_distances
from sqlmodel import Session, select, func

from app.db.database import get_session
from app.models.monthly_metric import MonthlyMetric
from app.models.headline import Headline
from app.models.outlet_month_centroid import OutletMonthCentroid

router = APIRouter(prefix="/months", tags=["case-study"])


@router.get("/{year_month}/sample-headlines-by-outlet")
def get_sample_headlines_by_outlet(
    year_month: str,
    outlet_1: str = Query(...),
    outlet_2: str = Query(...),
    limit: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_session),
):
    stmt_1 = (
        select(Headline)
        .where(Headline.year_month == year_month)
        .where(Headline.media_name == outlet_1)
        .limit(limit)
    )
    stmt_2 = (
        select(Headline)
        .where(Headline.year_month == year_month)
        .where(Headline.media_name == outlet_2)
        .limit(limit)
    )

    rows_1 = session.exec(stmt_1).all()
    rows_2 = session.exec(stmt_2).all()

    return {
        "year_month": year_month,
        "outlet_1": outlet_1,
        "outlet_2": outlet_2,
        "outlet_1_headlines": [
            {
                "id": row.id,
                "title": row.title,
                "url": row.url,
                "publish_date": row.publish_date,
                "sentiment": row.sentiment,
                "sentiment_label": row.sentiment_label,
            }
            for row in rows_1
        ],
        "outlet_2_headlines": [
            {
                "id": row.id,
                "title": row.title,
                "url": row.url,
                "publish_date": row.publish_date,
                "sentiment": row.sentiment,
                "sentiment_label": row.sentiment_label,
            }
            for row in rows_2
        ],
    }


@router.get("/{year_month}/case-study")
def get_month_case_study(year_month: str, session: Session = Depends(get_session)):
    metric_stmt = select(MonthlyMetric).where(MonthlyMetric.year_month == year_month)
    metric = session.exec(metric_stmt).first()

    if not metric:
        raise HTTPException(status_code=404, detail="Month not found")

    centroids_stmt = (
        select(OutletMonthCentroid)
        .where(OutletMonthCentroid.year_month == year_month)
        .order_by(OutletMonthCentroid.media_name)
    )
    centroids = session.exec(centroids_stmt).all()

    if len(centroids) < 2:
        raise HTTPException(status_code=404, detail="Not enough centroid data for this month")

    vectors = np.array([row.centroid for row in centroids], dtype=float)
    names = [row.media_name for row in centroids]

    dist_matrix = cosine_distances(vectors)
    i, j = np.unravel_index(np.argmax(dist_matrix), dist_matrix.shape)

    outlet_1 = names[i]
    outlet_2 = names[j]
    max_distance = float(dist_matrix[i, j])

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
    top_outlets = session.exec(top_outlets_stmt).all()

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

    headlines_1_stmt = (
        select(Headline)
        .where(Headline.year_month == year_month)
        .where(Headline.media_name == outlet_1)
        .limit(5)
    )
    headlines_2_stmt = (
        select(Headline)
        .where(Headline.year_month == year_month)
        .where(Headline.media_name == outlet_2)
        .limit(5)
    )

    headlines_1 = session.exec(headlines_1_stmt).all()
    headlines_2 = session.exec(headlines_2_stmt).all()

    return {
        "year_month": year_month,
        "summary": {
            "headline_count_before_anchor": metric.headline_count_before_anchor,
            "headline_count_after_anchor": metric.headline_count_after_anchor,
            "num_outlets": metric.num_outlets,
            "polarization_score": metric.polarization_score,
            "mean_sentiment": metric.mean_sentiment,
        },
        "top_outlets": [
            {
                "media_name": row.media_name,
                "headline_count": row.headline_count,
            }
            for row in top_outlets
        ],
        "sentiment_distribution": sentiment_distribution,
        "most_divergent_pair": {
            "outlet_1": outlet_1,
            "outlet_2": outlet_2,
            "cosine_distance": max_distance,
        },
        "outlet_1_headlines": [
            {
                "id": row.id,
                "title": row.title,
                "url": row.url,
                "publish_date": row.publish_date,
                "sentiment": row.sentiment,
                "sentiment_label": row.sentiment_label,
            }
            for row in headlines_1
        ],
        "outlet_2_headlines": [
            {
                "id": row.id,
                "title": row.title,
                "url": row.url,
                "publish_date": row.publish_date,
                "sentiment": row.sentiment,
                "sentiment_label": row.sentiment_label,
            }
            for row in headlines_2
        ],
    }