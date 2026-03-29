from datetime import datetime
import os

from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from app.core.config import UPLOAD_DIR
from app.db.database import get_session
from app.models.upload import Upload
from app.models.pipeline_run import PipelineRun
from app.models.headline import Headline
from app.models.headline_embedding import HeadlineEmbedding
from app.models.outlet_month_centroid import OutletMonthCentroid
from app.models.monthly_metric import MonthlyMetric

router = APIRouter(prefix="/dashboard", tags=["system"])


@router.get("/data-coverage")
def get_data_coverage(session: Session = Depends(get_session)):
    total_uploads = session.exec(select(func.count(Upload.id))).one()
    total_headlines = session.exec(select(func.count(Headline.id))).one()
    total_embeddings = session.exec(select(func.count(HeadlineEmbedding.id))).one()
    total_centroids = session.exec(select(func.count(OutletMonthCentroid.id))).one()
    total_monthly_metrics = session.exec(select(func.count(MonthlyMetric.id))).one()

    first_month = session.exec(select(func.min(MonthlyMetric.year_month))).one()
    last_month = session.exec(select(func.max(MonthlyMetric.year_month))).one()
    active_outlets = session.exec(select(func.count(func.distinct(Headline.media_name)))).one()
    covered_months = session.exec(select(func.count(func.distinct(MonthlyMetric.year_month)))).one()

    return {
        "total_uploads": total_uploads,
        "total_headlines": total_headlines,
        "total_embeddings": total_embeddings,
        "total_centroids": total_centroids,
        "total_monthly_metrics": total_monthly_metrics,
        "first_month": first_month,
        "last_month": last_month,
        "covered_months": covered_months,
        "active_outlets": active_outlets,
    }


@router.get("/health")
def get_system_health(session: Session = Depends(get_session)):
    db_connected = True

    uploads_folder_exists = os.path.exists(UPLOAD_DIR)

    upload_count = session.exec(select(func.count(Upload.id))).one()
    headline_count = session.exec(select(func.count(Headline.id))).one()
    embedding_count = session.exec(select(func.count(HeadlineEmbedding.id))).one()
    centroid_count = session.exec(select(func.count(OutletMonthCentroid.id))).one()
    monthly_metric_count = session.exec(select(func.count(MonthlyMetric.id))).one()

    latest_run_stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1)
    latest_run = session.exec(latest_run_stmt).first()

    return {
        "database_connected": db_connected,
        "uploads_folder_exists": uploads_folder_exists,
        "upload_count": upload_count,
        "headline_count": headline_count,
        "embedding_count": embedding_count,
        "centroid_count": centroid_count,
        "monthly_metric_count": monthly_metric_count,
        "latest_run": {
            "id": latest_run.id,
            "status": latest_run.status,
            "current_stage": latest_run.current_stage,
            "progress_percent": latest_run.progress_percent,
            "message": latest_run.message,
            "error_message": latest_run.error_message,
            "started_at": latest_run.started_at,
            "finished_at": latest_run.finished_at,
        } if latest_run else None,
        "checked_at": datetime.utcnow(),
    }