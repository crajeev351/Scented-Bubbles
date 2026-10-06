"""Syncs all media and upload assets from local storage to Supabase Storage bucket."""
import os
import sys
import mimetypes
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "app" / "static" / "uploads"

# Read Supabase settings from .env
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://wbnwicvdekusaallpokg.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET = os.environ.get("SUPABASE_BUCKET", "media")

if not SUPABASE_KEY:
    print("ERROR: SUPABASE_KEY / SUPABASE_SERVICE_ROLE_KEY missing from environment.")
    sys.exit(1)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "x-upsert": "true",
}

def sync_directory(directory: Path):
    if not directory.exists():
        print(f"Directory {directory} does not exist.")
        return

    files = [f for f in directory.iterdir() if f.is_file()]
    print(f"Found {len(files)} files to sync from {directory.name}...")

    success_count = 0
    fail_count = 0

    for idx, file_path in enumerate(files, 1):
        filename = file_path.name
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = "image/webp" if filename.endswith(".webp") else "application/octet-stream"

        upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{filename}"
        req_headers = dict(headers)
        req_headers["Content-Type"] = content_type

        try:
            with open(file_path, "rb") as f:
                data = f.read()

            res = requests.post(upload_url, data=data, headers=req_headers, timeout=20)
            if res.status_code in (200, 201):
                success_count += 1
                if idx % 10 == 0 or idx == len(files):
                    print(f"[{idx}/{len(files)}] Synced: {filename} ({len(data)} bytes)")
            else:
                fail_count += 1
                print(f"[{idx}/{len(files)}] Failed {filename}: HTTP {res.status_code} - {res.text}")
        except Exception as e:
            fail_count += 1
            print(f"[{idx}/{len(files)}] Error {filename}: {e}")

    print(f"\nFinished syncing {directory.name}: {success_count} succeeded, {fail_count} failed.")

if __name__ == "__main__":
    print(f"Starting Supabase Storage sync to bucket '{BUCKET}' at {SUPABASE_URL}...")
    sync_directory(UPLOADS_DIR)
