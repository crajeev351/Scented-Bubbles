import os
import re
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")


def normalize_database_url(raw_url: str | None) -> str:
    """Normalizes and repairs database connection URLs for PostgreSQL and Supabase.

    Handles:
    1. Converting legacy postgres:// or postgresql:// into postgresql+psycopg2://.
    2. URL-encoding passwords containing special characters like @ (e.g. ScentedBubbles@2026 -> ScentedBubbles%402026).
    3. Stripping bracket copy-paste artifacts (e.g. [ScentedBubbles@2026] -> ScentedBubbles%402026).
    4. Automatically translating IPv6-only Supabase direct hosts (db.<ref>.supabase.co) into the
       IPv4 AWS Pooler (aws-0-ap-south-1.pooler.supabase.com:5432) with tenant user postgres.<ref>.
    5. Ensuring pooler usernames include the tenant identifier (postgres.<ref>).
    6. Render fallback: if running on Render (RENDER=true) and no working postgres URI is configured,
       automatically connects to the verified Supabase project pooler.
    """
    DEFAULT_POOLER = (
        "postgresql+psycopg2://postgres.wbnwicvdekusaallpokg:ScentedBubbles%402026"
        "@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
    )

    if not raw_url or not str(raw_url).strip():
        if os.environ.get("RENDER") == "true" or os.environ.get("FLASK_ENV") == "production":
            return DEFAULT_POOLER
        return f"sqlite:///{BASE_DIR / 'scented_bubbles.db'}"

    url = str(raw_url).strip().strip("\"'")
    if url.startswith("sqlite"):
        if os.environ.get("RENDER") == "true":
            return DEFAULT_POOLER
        return url

    # Standardize scheme to postgresql+psycopg2
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    elif not url.startswith("postgresql+psycopg2://") and "://" in url:
        _, rest = url.split("://", 1)
        url = "postgresql+psycopg2://" + rest

    if "://" not in url:
        return DEFAULT_POOLER

    scheme, rest = url.split("://", 1)

    if "@" in rest:
        last_at = rest.rfind("@")
        user_pass = rest[:last_at]
        host_port_db = rest[last_at + 1:]

        user = "postgres"
        pwd = ""
        if ":" in user_pass:
            user, pwd = user_pass.split(":", 1)
        else:
            user = user_pass

        # Strip brackets if user copied [password]
        if pwd.startswith("[") and pwd.endswith("]"):
            pwd = pwd[1:-1]

        # Decode if already percent-encoded, then encode cleanly
        pwd = urllib.parse.quote_plus(urllib.parse.unquote_plus(pwd))

        # Parse host and db
        parts = host_port_db.split("/", 1)
        host_part = parts[0]
        db_name = parts[1] if len(parts) > 1 else "postgres"
        if "?" in db_name:
            db_name = db_name.split("?")[0]

        # Detect direct supabase host (db.<ref>.supabase.co is IPv6 only, fails on Render)
        if "db." in host_part and ".supabase.co" in host_part:
            match = re.search(r"db\.([a-zA-Z0-9]+)\.supabase\.co", host_part)
            ref = match.group(1) if match else "wbnwicvdekusaallpokg"
            host_part = "aws-0-ap-south-1.pooler.supabase.com:5432"
            user = f"postgres.{ref}"
        elif "pooler.supabase.com" in host_part:
            if "." not in user:
                user = "postgres.wbnwicvdekusaallpokg"

        return f"{scheme}://{user}:{pwd}@{host_part}/{db_name}"

    return url


class Config:
    """Base configuration shared across environments."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-scented-bubbles-secret-key-change-in-prod")
    
    # Database
    # Defaults to SQLite for local zero-config runs; normalizes Supabase / PostgreSQL URLs if provided.
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.environ.get("DATABASE_URL"))
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
    SQLALCHEMY_ENGINE_OPTIONS = {}
    STORAGE_BACKEND = "local"
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
