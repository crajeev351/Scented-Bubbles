import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration shared across environments."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-scented-bubbles-secret-key-change-in-prod")
    
    # Database
    # Defaults to SQLite for local zero-config runs; normalizes Supabase / PostgreSQL URLs if provided.
    _raw_db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'scented_bubbles.db'}")
    if _raw_db_url.startswith("postgres://"):
        _raw_db_url = _raw_db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLAlchemy Engine Pool Options for Supabase PostgreSQL / Production stability
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
    if not SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
        SQLALCHEMY_ENGINE_OPTIONS["pool_size"] = 10
        SQLALCHEMY_ENGINE_OPTIONS["max_overflow"] = 5

    # Security & Sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Enabled in ProductionConfig
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days
    
    # File Uploads & Storage Backend
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "app" / "static" / "uploads"))
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")
    
    # Supabase Storage configuration
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "media")
    
    # S3 / Cloudinary configurations (production alternative)
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
    S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
    S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
    S3_REGION = os.environ.get("S3_REGION", "ap-south-1")
    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")
    S3_CUSTOM_DOMAIN = os.environ.get("S3_CUSTOM_DOMAIN", "")
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "scentedbubbles")

    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"

    # Notification & WhatsApp settings
    SUPPORT_WHATSAPP = os.environ.get("SUPPORT_WHATSAPP", "919876543210")
    NOTIFICATION_EMAIL = os.environ.get("NOTIFICATION_EMAIL", "owner@scentedbubbles.com")
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False  # For easier test automation
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
