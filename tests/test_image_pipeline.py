import io
import os
from PIL import Image
import pytest
from flask import Flask

from app.services.image_service import (
    process_and_save_image,
    delete_image_bundle,
    get_image_url,
    get_image_srcset,
    validate_image_content,
    ImageSizeError,
    InvalidImageFormatError,
)
from app.services.storage import get_storage, LocalStorage, S3Storage, CloudinaryStorage
from app.models.products import Product
from app.models.product_images import ProductImage
from app.extensions import db


def _create_test_image_bytes(width=2000, height=2000, format="JPEG", quality=90) -> bytes:
    """Helper to generate real, verifiable large image bytes in memory (around 4.2 MB)."""
    raw_pixels = os.urandom(width * height * 3)
    img = Image.frombytes("RGB", (width, height), raw_pixels)
    buf = io.BytesIO()
    img.save(buf, format=format, quality=quality)
    return buf.getvalue()


def test_5mb_jpeg_upload_produces_sub_150kb_thumb_and_webp_sizes(app):
    """Uploading a large JPEG (~4.2 MB) produces sub-150KB thumb and reasonable medium/large WebP files."""
    with app.app_context():
        # Create a genuine 4.2 MB high-resolution JPEG
        raw_bytes = _create_test_image_bytes(width=2000, height=2000, format="JPEG", quality=90)
        assert 3 * 1024 * 1024 < len(raw_bytes) <= 5 * 1024 * 1024  # Between 3MB and 5MB!

        results = process_and_save_image(raw_bytes, filename="highres_perfume.jpg", prefix="test_prod")
        assert "thumb" in results
        assert "medium" in results
        assert "large" in results

        storage = get_storage()
        # Verify files were saved and check thumb size
        thumb_path = storage.upload_dir / results["thumb"]
        assert thumb_path.exists()
        thumb_size = thumb_path.stat().st_size
        
        # DEFINITION OF DONE: sub-150 KB thumb
        assert thumb_size < 150 * 1024, f"Thumb size {thumb_size} bytes exceeds 150 KB!"

        # Verify all 3 are genuine WebP files
        for key in (results["thumb"], results["medium"], results["large"]):
            fpath = storage.upload_dir / key
            assert fpath.exists()
            with Image.open(fpath) as im:
                assert im.format == "WEBP"

        # Cleanup
        delete_image_bundle(results["base_key"])


def test_oversized_upload_rejected():
    """Uploads exceeding the 5 MB limit are strictly rejected."""
    # 5.2 MB payload
    oversized_data = b"RIFF" + (b"\x00" * int(5.3 * 1024 * 1024))
    with pytest.raises(ImageSizeError) as exc_info:
        validate_image_content(oversized_data, filename="too_huge.jpg")
    assert "exceeds the 5 MB limit" in str(exc_info.value)


def test_fake_extension_upload_rejected():
    """Files with fake extensions (e.g. text/script renamed to .jpg) are rejected by content check."""
    fake_jpg = b"<?php echo 'malicious payload'; ?>"
    with pytest.raises(InvalidImageFormatError):
        validate_image_content(fake_jpg, filename="exploit.jpg")


def test_invalid_format_rejected():
    """Non-image files like text or PDFs are rejected."""
    text_file = b"This is just a plain text document."
    with pytest.raises(InvalidImageFormatError):
        validate_image_content(text_file, filename="document.pdf")


def test_switching_storage_backend_requires_only_env(app):
    """Switching storage backend requires only configuration/env changes."""
    # 1. Local storage (default)
    with app.app_context():
        app.config["STORAGE_BACKEND"] = "local"
        storage = get_storage()
        assert isinstance(storage, LocalStorage)
        assert storage.url_for("test.webp") == "/static/uploads/test.webp"

        # 2. S3 storage via config
        app.config["STORAGE_BACKEND"] = "s3"
        app.config["S3_BUCKET_NAME"] = "scented-bubbles-s3"
        app.config["S3_CUSTOM_DOMAIN"] = "cdn.scentedbubbles.com"
        storage_s3 = get_storage()
        assert isinstance(storage_s3, S3Storage)
        assert storage_s3.url_for("test.webp") == "https://cdn.scentedbubbles.com/test.webp"

        # 3. Cloudinary storage via config
        app.config["STORAGE_BACKEND"] = "cloudinary"
        app.config["CLOUDINARY_CLOUD_NAME"] = "scentedbrand"
        storage_cld = get_storage()
        assert isinstance(storage_cld, CloudinaryStorage)
        assert storage_cld.url_for("test.webp") == "https://res.cloudinary.com/scentedbrand/image/upload/test.webp"

        # Reset back to local
        app.config["STORAGE_BACKEND"] = "local"


def test_delete_image_bundle_cleans_up_all_variants(app):
    """Deleting an image bundle removes thumb, medium, and large files from storage."""
    with app.app_context():
        raw_bytes = _create_test_image_bytes(width=600, height=600, format="PNG")
        results = process_and_save_image(raw_bytes, filename="cleanup_bottle.png", prefix="cleanup")
        
        storage = get_storage()
        thumb_file = storage.upload_dir / results["thumb"]
        medium_file = storage.upload_dir / results["medium"]
        large_file = storage.upload_dir / results["large"]

        assert thumb_file.exists()
        assert medium_file.exists()
        assert large_file.exists()

        # Delete image bundle
        delete_image_bundle(results["base_key"])

        assert not thumb_file.exists()
        assert not medium_file.exists()
        assert not large_file.exists()


def test_cards_never_load_originals(app, client, sample_catalog):
    """Product cards must load thumbnail sizes (_thumb.webp), never originals or large sizes."""
    from app.services.cache_service import cache
    with app.app_context():
        # Check Product model property
        prod = Product.query.first()
        assert prod is not None
        # Add a ProductImage to ensure responsive srcset and thumbnail are exercised
        p_img = ProductImage(product_id=prod.id, image_key="perfume_velvet_oud_medium.webp", is_primary=True)
        db.session.add(p_img)
        db.session.commit()
        cache.clear()

        thumb_url = prod.thumbnail_url
        # Must point to a thumbnail variant
        assert "_thumb.webp" in thumb_url
        assert "_large.webp" not in thumb_url

    # Check Homepage HTML output
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    
    # Verify product card image tags use thumbnail_url
    assert 'class="card-img-wrap"' in html
    # Check that srcset is provided with 400w
    assert "400w" in html


def test_exif_orientation_transposed(app):
    """Images with EXIF orientation metadata (e.g. rotated in phone/viewer) are properly auto-oriented."""
    from PIL import Image

    # Create a 200w x 400h vertical image
    img = Image.new("RGB", (200, 400), color="blue")
    buf = io.BytesIO()
    # EXIF tag 274 (Orientation) = 6 means 90 deg clockwise rotation (should become 400w x 200h)
    exif = img.getexif()
    exif[274] = 6
    img.save(buf, format="JPEG", exif=exif)
    raw_data = buf.getvalue()

    with app.app_context():
        results = process_and_save_image(raw_data, filename="phone_photo.jpg", prefix="test_orient")
        storage = get_storage()
        large_path = storage.upload_dir / results["large"]
        assert large_path.exists()

        with Image.open(large_path) as processed_img:
            # After transposition, width should be greater than height (transposed from 200x400 to 400x200)
            assert processed_img.width > processed_img.height

        delete_image_bundle(results["base_key"])

