from typing import List

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_distances, cosine_similarity
from sqlmodel import Session, select

from app.db.database import get_session
from app.models.headline import Headline
from app.models.headline_embedding import HeadlineEmbedding
from app.models.outlet_month_centroid import OutletMonthCentroid

router = APIRouter(prefix="", tags=["semantic"])

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


@router.get("/months/{year_month}/most-divergent-pair")
def get_most_divergent_pair(year_month: str, session: Session = Depends(get_session)):
    statement = (
        select(OutletMonthCentroid)
        .where(OutletMonthCentroid.year_month == year_month)
        .order_by(OutletMonthCentroid.media_name)
    )
    rows = session.exec(statement).all()

    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="Not enough centroid data for this month")

    vectors = np.array([row.centroid for row in rows], dtype=float)
    dist_matrix = cosine_distances(vectors)

    i, j = np.unravel_index(np.argmax(dist_matrix), dist_matrix.shape)

    outlet_1 = rows[i].media_name
    outlet_2 = rows[j].media_name
    max_distance = float(dist_matrix[i, j])

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
        "outlet_1": outlet_1,
        "outlet_2": outlet_2,
        "cosine_distance": max_distance,
        "outlet_1_headlines": [
            {
                "id": h.id,
                "title": h.title,
                "url": h.url,
                "sentiment": h.sentiment,
                "sentiment_label": h.sentiment_label,
            }
            for h in headlines_1
        ],
        "outlet_2_headlines": [
            {
                "id": h.id,
                "title": h.title,
                "url": h.url,
                "sentiment": h.sentiment,
                "sentiment_label": h.sentiment_label,
            }
            for h in headlines_2
        ],
    }


@router.get("/months/{year_month}/centroids")
def get_month_centroids(year_month: str, session: Session = Depends(get_session)):
    statement = (
        select(OutletMonthCentroid)
        .where(OutletMonthCentroid.year_month == year_month)
        .order_by(OutletMonthCentroid.media_name)
    )
    rows = session.exec(statement).all()

    if not rows:
        raise HTTPException(status_code=404, detail="No centroid data found for this month")

    result = []
    for row in rows:
        centroid_value = row.centroid
        if hasattr(centroid_value, "tolist"):
            centroid_value = centroid_value.tolist()
        else:
            centroid_value = list(centroid_value)

        result.append(
            {
                "media_name": row.media_name,
                "year_month": row.year_month,
                "num_headlines": row.num_headlines,
                "centroid": [float(x) for x in centroid_value],
            }
        )

    return result


@router.get("/months/{year_month}/semantic-space")
def get_month_semantic_space(year_month: str, session: Session = Depends(get_session)):
    statement = (
        select(OutletMonthCentroid)
        .where(OutletMonthCentroid.year_month == year_month)
        .order_by(OutletMonthCentroid.media_name)
    )
    rows = session.exec(statement).all()

    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="Not enough centroid data for this month")

    vectors = np.array([row.centroid for row in rows], dtype=float)

    pca = PCA(n_components=2)
    coords = pca.fit_transform(vectors)

    return {
        "year_month": year_month,
        "explained_variance_ratio": [float(x) for x in pca.explained_variance_ratio_],
        "points": [
            {
                "media_name": rows[i].media_name,
                "num_headlines": rows[i].num_headlines,
                "x": float(coords[i, 0]),
                "y": float(coords[i, 1]),
            }
            for i in range(len(rows))
        ],
    }


@router.get("/outlets/{media_name}/neighbors")
def get_outlet_neighbors(
    media_name: str,
    year_month: str = Query(...),
    top_k: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_session),
):
    statement = (
        select(OutletMonthCentroid)
        .where(OutletMonthCentroid.year_month == year_month)
        .order_by(OutletMonthCentroid.media_name)
    )
    rows = session.exec(statement).all()

    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="Not enough centroid data for this month")

    names = [row.media_name for row in rows]
    if media_name not in names:
        raise HTTPException(status_code=404, detail="Outlet not found for this month")

    vectors = np.array([row.centroid for row in rows], dtype=float)
    dist_matrix = cosine_distances(vectors)

    idx = names.index(media_name)
    distances = []

    for i, other_name in enumerate(names):
        if other_name == media_name:
            continue
        distances.append(
            {
                "media_name": other_name,
                "cosine_distance": float(dist_matrix[idx, i]),
            }
        )

    distances_sorted = sorted(distances, key=lambda x: x["cosine_distance"])

    nearest = distances_sorted[:top_k]
    farthest = distances_sorted[-top_k:][::-1]

    return {
        "media_name": media_name,
        "year_month": year_month,
        "nearest": nearest,
        "farthest": farthest,
    }


@router.get("/search/semantic")
def semantic_search(
    query: str = Query(..., min_length=3),
    top_k: int = Query(default=10, ge=1, le=50),
    similarity_threshold: float = Query(default=0.75, ge=0.0, le=1.0),
    session: Session = Depends(get_session),
):
    model = get_model()
    query_vec = model.encode([query], normalize_embeddings=True)

    emb_stmt = select(HeadlineEmbedding)
    emb_rows = session.exec(emb_stmt).all()

    if not emb_rows:
        raise HTTPException(status_code=404, detail="No embeddings available")

    headline_ids = [row.headline_id for row in emb_rows]
    vectors = np.array([row.embedding for row in emb_rows], dtype=float)

    sims = cosine_similarity(query_vec, vectors)[0]

    matched_indices = np.where(sims >= similarity_threshold)[0]
    if len(matched_indices) == 0:
        return {
            "query": query,
            "similarity_threshold": similarity_threshold,
            "matches": [],
        }

    ranked = sorted(
        [(idx, float(sims[idx])) for idx in matched_indices],
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    selected_ids = [headline_ids[idx] for idx, _ in ranked]

    headline_stmt = select(Headline).where(Headline.id.in_(selected_ids))
    headline_rows = session.exec(headline_stmt).all()
    headline_map = {row.id: row for row in headline_rows}

    matches = []
    for idx, score in ranked:
        headline_id = headline_ids[idx]
        row = headline_map.get(headline_id)
        if not row:
            continue

        matches.append(
            {
                "id": row.id,
                "title": row.title,
                "media_name": row.media_name,
                "publish_date": row.publish_date,
                "year_month": row.year_month,
                "url": row.url,
                "sentiment": row.sentiment,
                "sentiment_label": row.sentiment_label,
                "similarity": score,
            }
        )

    return {
        "query": query,
        "similarity_threshold": similarity_threshold,
        "matches": matches,
    }