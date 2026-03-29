import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sklearn.cluster import KMeans
from sqlmodel import Session, select

from app.db.database import get_session
from app.models.outlet_month_centroid import OutletMonthCentroid

router = APIRouter(prefix="/months", tags=["clusters"])


@router.get("/{year_month}/clusters")
def get_month_clusters(
    year_month: str,
    n_clusters: int = Query(default=4, ge=2, le=10),
    session: Session = Depends(get_session),
):
    stmt = (
        select(OutletMonthCentroid)
        .where(OutletMonthCentroid.year_month == year_month)
        .order_by(OutletMonthCentroid.media_name)
    )
    rows = session.exec(stmt).all()

    if len(rows) < n_clusters:
        raise HTTPException(
            status_code=400,
            detail="Not enough outlet centroids for requested cluster count",
        )

    X = np.array([row.centroid for row in rows], dtype=float)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    clusters = {}
    for i, row in enumerate(rows):
        cluster_id = int(labels[i])
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(
            {
                "media_name": row.media_name,
                "num_headlines": row.num_headlines,
            }
        )

    return {
        "year_month": year_month,
        "n_clusters": n_clusters,
        "clusters": [
            {
                "cluster_id": cluster_id,
                "size": len(outlets),
                "outlets": outlets,
            }
            for cluster_id, outlets in sorted(clusters.items())
        ],
    }