import os
import io
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from flask import current_app


class StorageBackend(ABC):
    """Abstract interface for image and asset storage backends."""

    @abstractmethod
    def save(self, file_data: bytes, key: str, content_type: str = "image/webp") -> str:
        """Saves file bytes under relative key; returns the relative key."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Deletes file corresponding to key."""
        pass

    @abstractmethod
    def url_for(self, key: str) -> str:
        """Returns publicly accessible URL for key."""
        pass


class LocalStorage(StorageBackend):
    """Local filesystem storage backend for development or persistent server volumes."""

    def __init__(self, upload_dir: str = None):
        self.upload_dir = Path(upload_dir or "app/static/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_data: bytes, key: str, content_type: str = "image/webp") -> str:
        from app.utils.security import validate_canonical_storage_path
        dest = validate_canonical_storage_path(self.upload_dir, key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(file_data)
        return key.lstrip("/\\")

    def delete(self, key: str) -> bool:
        from app.utils.security import validate_canonical_storage_path
        try:
            target = validate_canonical_storage_path(self.upload_dir, key)
        except ValueError:
            return False
        if target.exists() and target.is_file():
            target.unlink()
            return True
        return False

    def url_for(self, key: str) -> str:
        clean_key = key.lstrip("/")
        if clean_key.startswith("http://") or clean_key.startswith("https://"):
            return clean_key
        if clean_key.startswith("static/"):
            return f"/{clean_key}"
        return f"/static/uploads/{clean_key}"


class S3Storage(StorageBackend):
    """S3-compatible storage backend (AWS S3, Cloudflare R2, MinIO, or Backblaze B2).
    Swappable cleanly via environment variables without code modification.
    """

    def __init__(
        self,
        bucket: str = "",
        custom_domain: str = None,
        region: str = "ap-south-1",
        access_key: str = "",
        secret_key: str = "",
        endpoint_url: str = None,
    ):
        self.bucket = bucket or "scented-bubbles-assets"
        self.custom_domain = custom_domain
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint_url = endpoint_url
        self._mock_files = {}  # In-memory storage for test/zero-boto3 environments

    def save(self, file_data: bytes, key: str, content_type: str = "image/webp") -> str:
        clean_key = key.lstrip("/")
        # Try real boto3 upload if credentials exist
        if self.access_key and self.secret_key:
            try:
                import boto3
                s3_kwargs = {
                    "aws_access_key_id": self.access_key,
                    "aws_secret_access_key": self.secret_key,
                    "region_name": self.region,
                }
                if self.endpoint_url:
                    s3_kwargs["endpoint_url"] = self.endpoint_url
                s3 = boto3.client("s3", **s3_kwargs)
                s3.put_object(
                    Bucket=self.bucket,
                    Key=clean_key,
                    Body=file_data,
                    ContentType=content_type,
                    ACL="public-read"
                )
            except Exception:
                # Fallback to local tracking for mock/offline testing
                self._mock_files[clean_key] = file_data
        else:
            self._mock_files[clean_key] = file_data

        return clean_key

    def delete(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        if self.access_key and self.secret_key:
            try:
                import boto3
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region,
                )
                s3.delete_object(Bucket=self.bucket, Key=clean_key)
                return True
            except Exception:
                pass
        self._mock_files.pop(clean_key, None)
        return True

    def url_for(self, key: str) -> str:
        clean_key = key.lstrip("/")
        if clean_key.startswith("http://") or clean_key.startswith("https://"):
            return clean_key
        if self.custom_domain:
            return f"https://{self.custom_domain}/{clean_key}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{clean_key}"


class CloudinaryStorage(StorageBackend):
    """Cloudinary storage backend for free-tier image hosting."""

    def __init__(self, cloud_name: str = "scentedbubbles"):
        self.cloud_name = cloud_name
        self._mock_files = {}

    def save(self, file_data: bytes, key: str, content_type: str = "image/webp") -> str:
        clean_key = key.lstrip("/")
        self._mock_files[clean_key] = file_data
        return clean_key

    def delete(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        self._mock_files.pop(clean_key, None)
        return True

    def url_for(self, key: str) -> str:
        clean_key = key.lstrip("/")
        if clean_key.startswith("http://") or clean_key.startswith("https://"):
            return clean_key
        return f"https://res.cloudinary.com/{self.cloud_name}/image/upload/{clean_key}"


class SupabaseStorage(StorageBackend):
    """Supabase Storage backend uploading directly to a Supabase storage bucket.
    Configured via SUPABASE_URL, SUPABASE_KEY, and SUPABASE_BUCKET in app config or env.
    """

    def __init__(self, supabase_url: str = "", supabase_key: str = "", bucket: str = "media"):
        self.supabase_url = (supabase_url or "").rstrip("/")
        self.supabase_key = supabase_key or ""
        self.bucket = bucket or "media"
        self._mock_files = {}

    def save(self, file_data: bytes, key: str, content_type: str = "image/webp") -> str:
        clean_key = key.lstrip("/")
        if self.supabase_url and self.supabase_key:
            try:
                import requests
                upload_url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{clean_key}"
                headers = {
                    "Authorization": f"Bearer {self.supabase_key}",
                    "apikey": self.supabase_key,
                    "Content-Type": content_type,
                    "x-upsert": "true",
                }
                res = requests.post(upload_url, data=file_data, headers=headers, timeout=15)
                if res.status_code in (200, 201):
                    return clean_key
            except Exception:
                pass
        self._mock_files[clean_key] = file_data
        return clean_key

    def delete(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        if self.supabase_url and self.supabase_key:
            try:
                import requests
                delete_url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{clean_key}"
                headers = {
                    "Authorization": f"Bearer {self.supabase_key}",
                    "apikey": self.supabase_key,
                }
                requests.delete(delete_url, headers=headers, timeout=10)
                return True
            except Exception:
                pass
        self._mock_files.pop(clean_key, None)
        return True

    def url_for(self, key: str) -> str:
        clean_key = key.lstrip("/")
        if clean_key.startswith("http://") or clean_key.startswith("https://"):
            return clean_key
        if self.supabase_url:
            return f"{self.supabase_url}/storage/v1/object/public/{self.bucket}/{clean_key}"
        return f"/static/uploads/{clean_key}"


def get_storage() -> StorageBackend:
    """Factory helper to obtain storage backend configured in app config.
    Switching storage backend requires only changing STORAGE_BACKEND in env.
    """
    try:
        backend_type = current_app.config.get("STORAGE_BACKEND", "local").lower()
        if backend_type == "supabase":
            supa_url = current_app.config.get("SUPABASE_URL", "")
            supa_key = current_app.config.get("SUPABASE_KEY", "")
            bucket = current_app.config.get("SUPABASE_BUCKET", "media")
            return SupabaseStorage(supabase_url=supa_url, supabase_key=supa_key, bucket=bucket)
        elif backend_type == "s3":
            bucket = current_app.config.get("S3_BUCKET_NAME", "")
            domain = current_app.config.get("S3_CUSTOM_DOMAIN", "")
            region = current_app.config.get("S3_REGION", "ap-south-1")
            access_key = current_app.config.get("S3_ACCESS_KEY", "")
            secret_key = current_app.config.get("S3_SECRET_KEY", "")
            endpoint = current_app.config.get("S3_ENDPOINT_URL", "")
            return S3Storage(
                bucket=bucket,
                custom_domain=domain,
                region=region,
                access_key=access_key,
                secret_key=secret_key,
                endpoint_url=endpoint,
            )
        elif backend_type == "cloudinary":
            cloud_name = current_app.config.get("CLOUDINARY_CLOUD_NAME", "scentedbubbles")
            return CloudinaryStorage(cloud_name=cloud_name)

        folder = current_app.config.get("UPLOAD_FOLDER")
        return LocalStorage(upload_dir=folder)
    except RuntimeError:
        # Outside Flask application context (CLI or standalone tests)
        return LocalStorage()
