from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import PROJECT_NAME
from app.db.database import init_db
from app.routes.auth import router as auth_router
from app.routes.uploads import router as uploads_router
from app.routes.pipeline import router as pipeline_router

from app.models.upload import Upload  
from app.models.pipeline_run import PipelineRun  
from app.models.headline import Headline  
from app.models.headline_embedding import HeadlineEmbedding  
from app.models.outlet_month_centroid import OutletMonthCentroid  
from app.models.monthly_metric import MonthlyMetric  
from app.routes.uploads_history import router as uploads_history_router
from app.routes.months import router as months_router

app = FastAPI(title=PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(auth_router)
app.include_router(uploads_router)
app.include_router(pipeline_router)
app.include_router(uploads_history_router)
app.include_router(months_router)


@app.get("/")
def root():
    return {"message": f"{PROJECT_NAME} backend is running"}