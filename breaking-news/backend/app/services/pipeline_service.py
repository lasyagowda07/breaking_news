import os
from datetime import datetime
from typing import List

import nltk
import numpy as np
import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity, cosine_distances
from sqlmodel import Session, select

from app.core.config import UPLOAD_DIR
from app.db.database import engine
from app.models.pipeline_run import PipelineRun
from app.models.headline import Headline
from app.models.headline_embedding import HeadlineEmbedding
from app.models.outlet_month_centroid import OutletMonthCentroid
from app.models.monthly_metric import MonthlyMetric

MODEL_NAME = "all-MiniLM-L6-v2"
SIM_THRESHOLD = 0.30
MAX_TITLE_LEN = 250
REQUIRED_COLUMNS = ["publish_date", "media_name", "language", "title", "url"]

ANCHOR_TEXT = """
climate change global warming carbon emissions greenhouse gases
renewable energy fossil fuels net zero climate policy climate crisis
""".strip()


def update_run(
    session: Session,
    run_id: int,
    status: str,
    stage: str,
    progress: int,
    message: str = None,
    error_message: str = None,
):
    run = session.get(PipelineRun, run_id)
    if not run:
        return

    run.status = status
    run.current_stage = stage
    run.progress_percent = progress
    run.message = message
    run.error_message = error_message

    if status in ["completed", "failed"]:
        run.finished_at = datetime.utcnow()

    session.add(run)
    session.commit()


def clear_derived_tables(session: Session):
    session.exec(HeadlineEmbedding.__table__.delete())
    session.exec(OutletMonthCentroid.__table__.delete())
    session.exec(MonthlyMetric.__table__.delete())
    session.exec(Headline.__table__.delete())
    session.commit()


def read_csv_with_fallback(file_path: str) -> pd.DataFrame:
    encodings = ["utf-8", "latin-1", "cp1252"]
    last_error = None

    for encoding in encodings:
        # First try fast/default parser
        try:
            return pd.read_csv(file_path, encoding=encoding)
        except Exception as e:
            last_error = e

        # Then try more forgiving parser
        try:
            return pd.read_csv(
                file_path,
                encoding=encoding,
                engine="python",
                on_bad_lines="skip",
            )
        except Exception as e:
            last_error = e

    raise ValueError(f"Could not read CSV {file_path}: {last_error}")


def load_all_uploaded_csvs(upload_dir: str) -> pd.DataFrame:
    csv_files = sorted(
        [
            os.path.join(upload_dir, f)
            for f in os.listdir(upload_dir)
            if f.lower().endswith(".csv")
        ]
    )

    if not csv_files:
        raise ValueError("No CSV files found in uploads folder")

    dfs = []
    for path in csv_files:
        df = read_csv_with_fallback(path)
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    return combined


def preprocess_raw(df_raw: pd.DataFrame):
    df_raw.columns = [str(c).strip().lower() for c in df_raw.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df_raw.columns]
    if missing:
        raise ValueError(f"Missing required columns after standardization: {', '.join(missing)}")

    df1 = df_raw[["publish_date", "media_name", "language", "title", "url"]].copy()

    df1["media_name"] = df1["media_name"].astype(str).str.lower().str.strip()
    df1["title"] = df1["title"].astype(str).str.strip()
    df1["language"] = df1["language"].astype(str).str.lower().str.strip()
    df1["url"] = df1["url"].astype(str).str.strip()

    df1["publish_date"] = pd.to_datetime(df1["publish_date"], errors="coerce")
    df1 = df1.dropna(subset=["publish_date", "title"])
    df1 = df1[df1["language"] == "en"].copy()

    df1["date"] = df1["publish_date"].dt.date
    df1["year"] = df1["publish_date"].dt.year
    df1["month"] = df1["publish_date"].dt.month
    df1["year_month"] = df1["publish_date"].dt.to_period("M").astype(str)

    before_anchor_counts = df1["year_month"].value_counts().sort_index().to_dict()

    df2 = df1.copy()
    df2 = df2[df2["title"].apply(len) <= MAX_TITLE_LEN].copy()

    df2["title_clean"] = (
        df2["title"]
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    df2 = df2.drop_duplicates(subset=["media_name", "title_clean"]).copy()

    return df2, before_anchor_counts


def label_sentiment(x: float) -> str:
    if x >= 0.05:
        return "positive"
    if x <= -0.05:
        return "negative"
    return "neutral"


def process_all_uploads(run_id: int):
    with Session(engine) as session:
        try:
            update_run(session, run_id, "running", "loading_uploads", 5, "Loading all uploaded CSV files")

            clear_derived_tables(session)

            df_raw = load_all_uploaded_csvs(UPLOAD_DIR)

            update_run(session, run_id, "running", "preprocessing", 20, "Preprocessing raw data")
            df_clean, before_anchor_counts = preprocess_raw(df_raw)

            update_run(session, run_id, "running", "anchor_filtering", 40, "Applying semantic anchor filter")
            model = SentenceTransformer(MODEL_NAME)
            anchor_vec = model.encode([ANCHOR_TEXT], convert_to_numpy=True)

            title_embeddings_for_anchor = model.encode(
                df_clean["title_clean"].tolist(),
                batch_size=64,
                convert_to_numpy=True,
                show_progress_bar=False,
            )

            similarities = cosine_similarity(title_embeddings_for_anchor, anchor_vec).reshape(-1)
            df_clean["anchor_similarity"] = similarities

            df_climate = df_clean[df_clean["anchor_similarity"] >= SIM_THRESHOLD].copy()

            update_run(session, run_id, "running", "sentiment", 55, "Running sentiment analysis")
            try:
                nltk.data.find("sentiment/vader_lexicon.zip")
            except LookupError:
                nltk.download("vader_lexicon")

            sia = SentimentIntensityAnalyzer()
            df_climate["sentiment"] = df_climate["title_clean"].apply(
                lambda t: sia.polarity_scores(t)["compound"]
            )
            df_climate["sentiment_label"] = df_climate["sentiment"].apply(label_sentiment)

            update_run(session, run_id, "running", "embeddings", 70, "Creating headline embeddings")
            embeddings = model.encode(
                df_climate["title_clean"].tolist(),
                batch_size=64,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            df_climate["embedding"] = list(embeddings)

            update_run(session, run_id, "running", "storing_headlines", 80, "Storing processed headlines and embeddings")

            headline_id_map = []

            for _, row in df_climate.iterrows():
                headline = Headline(
                    publish_date=row["publish_date"].to_pydatetime(),
                    media_name=row["media_name"],
                    language=row["language"],
                    title=row["title"],
                    url=row["url"],
                    date=row["date"],
                    year=int(row["year"]),
                    month=int(row["month"]),
                    year_month=row["year_month"],
                    title_clean=row["title_clean"],
                    anchor_similarity=float(row["anchor_similarity"]),
                    sentiment=float(row["sentiment"]),
                    sentiment_label=row["sentiment_label"],
                )
                session.add(headline)
                session.commit()
                session.refresh(headline)

                emb = HeadlineEmbedding(
                    headline_id=headline.id,
                    embedding=row["embedding"].tolist(),
                )
                session.add(emb)
                headline_id_map.append(headline.id)

            session.commit()

            update_run(session, run_id, "running", "centroids", 88, "Computing outlet-month centroids")
            grouped = df_climate.groupby(["media_name", "year_month"])
            centroids = []

            for (outlet, ym), group in grouped:
                if len(group) < 3:
                    continue

                vectors = np.stack(group["embedding"].values)
                centroid = np.mean(vectors, axis=0)

                centroids.append({
                    "media_name": outlet,
                    "year_month": ym,
                    "centroid": centroid,
                    "num_headlines": len(group),
                })

            centroids_df = pd.DataFrame(centroids)

            if not centroids_df.empty:
                for _, row in centroids_df.iterrows():
                    obj = OutletMonthCentroid(
                        media_name=row["media_name"],
                        year_month=row["year_month"],
                        num_headlines=int(row["num_headlines"]),
                        centroid=row["centroid"].tolist(),
                    )
                    session.add(obj)
                session.commit()

            update_run(session, run_id, "running", "monthly_metrics", 95, "Computing monthly metrics")
            monthly_metrics = []

            if not centroids_df.empty:
                months = sorted(centroids_df["year_month"].unique())

                monthly_sentiment = df_climate.groupby("year_month")["sentiment"].mean().to_dict()
                after_anchor_counts = df_climate["year_month"].value_counts().sort_index().to_dict()

                for month in months:
                    month_data = centroids_df[centroids_df["year_month"] == month]
                    vectors = np.stack(month_data["centroid"].values)
                    distances = cosine_distances(vectors)
                    triu_indices = np.triu_indices_from(distances, k=1)
                    pairwise_values = distances[triu_indices]
                    avg_distance = float(np.mean(pairwise_values))

                    metric = MonthlyMetric(
                        year_month=month,
                        headline_count_before_anchor=int(before_anchor_counts.get(month, 0)),
                        headline_count_after_anchor=int(after_anchor_counts.get(month, 0)),
                        num_outlets=int(len(month_data)),
                        polarization_score=avg_distance,
                        mean_sentiment=float(monthly_sentiment.get(month, 0.0)),
                    )
                    monthly_metrics.append(metric)

                for metric in monthly_metrics:
                    session.add(metric)
                session.commit()

            update_run(session, run_id, "completed", "completed", 100, "Pipeline completed successfully")

        except Exception as e:
            update_run(
                session,
                run_id,
                "failed",
                "failed",
                100,
                message="Pipeline failed",
                error_message=str(e),
            )