from fastapi import APIRouter, HTTPException
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.config import ADMIN_EMAIL, ADMIN_PASSWORD, PROJECT_NAME
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    if data.email != ADMIN_EMAIL or data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=data.email)
    return TokenResponse(access_token=token)


@router.get("/project")
def get_project_info():
    return {"project_name": PROJECT_NAME}