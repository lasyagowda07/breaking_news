import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_NAME = os.getenv("PROJECT_NAME", "Breaking News")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@breakingnews.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change_this_now")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-this")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/breaking_news_db")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")