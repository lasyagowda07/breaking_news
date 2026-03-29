from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from app.db.database import get_session
from app.models.pipeline_run import PipelineRun
from app.models.upload import Upload
from app.models.headline import Headline
from app.models.monthly_metric import MonthlyMetric

router = APIRouter(prefix="/dashboard", tags=["admin-dashboard"])


@router.get("/latest-run")
def get_latest_run(session: Session = Depends(get_session)):
    stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1)
    run = session.exec(stmt).first()

    if not run:
        return None

    return {
        "id": run.id,
        "status": run.status,
        "current_stage": run.current_stage,
        "progress_percent": run.progress_percent,
        "message": run.message,
        "error_message": run.error_message,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


@router.get("/runs")
def list_pipeline_runs(session: Session = Depends(get_session)):
    stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc())
    runs = session.exec(stmt).all()

    return [
        {
            "id": run.id,
            "status": run.status,
            "current_stage": run.current_stage,
            "progress_percent": run.progress_percent,
            "message": run.message,
            "error_message": run.error_message,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        }
        for run in runs
    ]


@router.get("/summary")
def get_dashboard_summary(session: Session = Depends(get_session)):
    total_uploads = session.exec(select(func.count(Upload.id))).one()
    total_headlines = session.exec(select(func.count(Headline.id))).one()
    total_months = session.exec(select(func.count(func.distinct(MonthlyMetric.year_month)))).one()
    total_outlets = session.exec(select(func.count(func.distinct(Headline.media_name)))).one()

    latest_month_stmt = (
        select(MonthlyMetric)
        .order_by(MonthlyMetric.year_month.desc())
        .limit(1)
    )
    latest_month = session.exec(latest_month_stmt).first()

    latest_run_stmt = (
        select(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )
    latest_run = session.exec(latest_run_stmt).first()

    return {
        "totals": {
            "uploads": total_uploads,
            "headlines": total_headlines,
            "months": total_months,
            "outlets": total_outlets,
        },
        "latest_month": {
            "year_month": latest_month.year_month,
            "headline_count_after_anchor": latest_month.headline_count_after_anchor,
            "num_outlets": latest_month.num_outlets,
            "polarization_score": latest_month.polarization_score,
            "mean_sentiment": latest_month.mean_sentiment,
        } if latest_month else None,
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
    }