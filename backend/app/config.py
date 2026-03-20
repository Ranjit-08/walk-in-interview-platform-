# app/config.py — Centralised configuration from environment variables

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Flask ──────────────────────────────────────────────────
    SECRET_KEY          = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
    DEBUG               = os.environ.get("FLASK_ENV") == "development"

    # ── Database (RDS MySQL) ───────────────────────────────────
    DB_HOST             = os.environ.get("DB_HOST", "localhost")
    DB_PORT             = int(os.environ.get("DB_PORT", 3306))
    DB_NAME             = os.environ.get("DB_NAME", "interview_platform")
    DB_USER             = os.environ.get("DB_USER", "root")
    DB_PASSWORD         = os.environ.get("DB_PASSWORD", "")

    # SQLAlchemy connection string
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    SQLALCHEMY_POOL_SIZE        = 10
    SQLALCHEMY_POOL_TIMEOUT     = 30
    SQLALCHEMY_POOL_RECYCLE     = 1800   # Recycle connections every 30 min
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── AWS ────────────────────────────────────────────────────
    AWS_REGION          = os.environ.get("AWS_REGION", "ap-south-1")

    # Cognito
    COGNITO_USER_POOL_ID  = os.environ.get("COGNITO_USER_POOL_ID")
    COGNITO_APP_CLIENT_ID = os.environ.get("COGNITO_APP_CLIENT_ID")
    COGNITO_REGION        = os.environ.get("COGNITO_REGION", "ap-south-1")

    # SES
    SES_SENDER_EMAIL    = os.environ.get("SES_SENDER_EMAIL")
    SES_REGION          = os.environ.get("SES_REGION", "ap-south-1")

    # Bedrock
    BEDROCK_REGION      = os.environ.get("BEDROCK_REGION", "ap-south-1")
    BEDROCK_MODEL_ID    = os.environ.get(
        "BEDROCK_MODEL_ID",
        "anthropic.claude-3-sonnet-20240229-v1:0"
    )

    # Frontend (for CORS)
    FRONTEND_URL        = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # Booking
    BOOKING_CODE_PREFIX = os.environ.get("BOOKING_CODE_PREFIX", "WI")