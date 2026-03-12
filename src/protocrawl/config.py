from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {
        "env_prefix": "PROTOCRAWL_",
        "env_file": ".env",
        "extra": "ignore",
    }

    # Database
    database_url: str = (
        "postgresql+asyncpg://protocrawl:protocrawl@localhost:5432/protocrawl"
    )

    # Google Cloud (optional for GCS/deployment)
    gcp_project: str = ""
    gcp_location: str = "us-central1"
    gcs_bucket: str = "protocrawl-artifacts"

    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-pro-preview"

    # Confidence thresholds
    auto_publish_threshold: float = 0.85
    review_required_threshold: float = 0.60

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_allow_origins: str = "*"

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_app_token: str = ""
    slack_review_channel: str = ""


settings = Settings()
