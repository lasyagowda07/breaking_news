from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.database import get_session
from app.models.pipeline_run import PipelineRun
from app.schemas.pipeline import PipelineRunResponse

router = APIRouter(prefix="/pipeline-runs", tags=["pipeline"])


@router.get("/{run_id}", response_model=PipelineRunResponse)
def get_pipeline_run(
    run_id: int,
    session: Session = Depends(get_session),
):
    run = session.get(PipelineRun, run_id)

    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return PipelineRunResponse(
        id=run.id,
        status=run.status,
        current_stage=run.current_stage,
        progress_percent=run.progress_percent,
        message=run.message,
        error_message=run.error_message,
    )