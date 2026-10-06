import io
import os
import uuid
import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename

from app.services.storage import get_storage


class ImageError(Exception):
    """Base exception for image processing errors."""
    pass


class ImageSizeError(ImageError):
    """Raised when uploaded image exceeds size limit (5 MB)."""
    pass


class InvalidImageFormatError(ImageError):
    """Raised when uploaded file is corrupted, fake extension, or unsupported format."""
    pass


# Strict configuration
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "MPO"}

# Responsive size specs (max width/height bounding box, quality)
SIZE_SPECS = {
    "thumb": {"max_dim": 400, "quality": 80},     # Cards / admin thumbnails (target < 150 KB)
    "medium": {"max_dim": 800, "quality": 82},    # Product detail page / modal
    "large": {"max_dim": 1200, "quality": 85},    # Zoom / full screen / hero banner
}


def validate_image_content(file_bytes: bytes, filename: str = "") -> Image.Image:
    """Validates real image content using Pillow. Rejects fake extensions and files > 5MB."""
    if not file_bytes:
        raise InvalidImageFormatError("No image data provided.")

    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise ImageSizeError(
            f"File size ({len(file_bytes) / (1024 * 1024):.2f} MB) exceeds the 5 MB limit."
        )

    # Validate image header and structure
    try:
        buf = io.BytesIO(file_bytes)
        img = Image.open(buf)
        img.verify()  # Verifies file integrity
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise InvalidImageFormatError(f"File is not a valid or recognizable image: {e}")

    # Re-open after verify() (Pillow verify closes/clears the internal file pointer)
    buf.seek(0)
    img = Image.open(buf)

    if img.format and img.format.upper() not in ALLOWED_FORMATS:
        raise InvalidImageFormatError(
            f"Image format '{img.format}' is not supported. Allowed: JPEG, PNG, WEBP."
        )

    # Automatically rotate/transpose image according to EXIF orientation tag (e.g. photos rotated in phone or image viewer)
    try:
        transposed = ImageOps.exif_transpose(img)
        if transposed is not None:
            img = transposed
    except Exception:
        pass

    return img


def resize_and_compress(image: Image.Image, max_dim: int, quality: int = 82) -> bytes:
    """Resizes image keeping aspect ratio and compresses to optimized WebP format."""
    # Work on a copy so multiple sizes can be generated from one source
    img = image.copy()

    # Convert modes like CMYK or Palette to RGB / RGBA for WebP
    if img.mode in ("RGBA", "LA"):
        # Keep alpha for transparency
        pass
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize keeping aspect ratio
    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    output = io.BytesIO()
    img.save(output, format="WEBP", quality=quality, method=4)
    return output.getvalue()


def process_and_save_image(
    file_storage_or_bytes,
    filename: str = "",
    prefix: str = "img",
    fit_dimensions: Optional[Tuple[int, int]] = None,
) -> Dict[str, str]:
    """Validates by content, enforces 5MB, resizes, compresses, and generates WebP thumb/medium/large.
    If fit_dimensions is specified (e.g. (800, 450) for category cards or (1920, 600) for hero banners),
    automatically crops from the center and scales to the exact target aspect ratio and dimensions without distortion.
    Returns dictionary with relative storage keys.
    """
    if hasattr(file_storage_or_bytes, "read"):
        filename = filename or getattr(file_storage_or_bytes, "filename", "image.jpg")
        file_bytes = file_storage_or_bytes.read()
    else:
        file_bytes = file_storage_or_bytes

    # Validate image bytes by content (not trusting extension)
    pil_image = validate_image_content(file_bytes, filename=filename)

    # Auto-fit & center-crop if specific card/banner dimensions are requested
    if fit_dimensions and len(fit_dimensions) == 2:
        target_w, target_h = int(fit_dimensions[0]), int(fit_dimensions[1])
        if target_w > 0 and target_h > 0:
            pil_image = ImageOps.fit(pil_image, (target_w, target_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

    # Secure base name with timestamp and short unique uuid
    safe_name = secure_filename(filename) if filename else "img"
    clean_stem = Path(safe_name).stem.replace(" ", "_")[:24]
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    rand_id = uuid.uuid4().hex[:6]
    base_key = f"{prefix}_{ts}_{clean_stem}_{rand_id}"

    storage = get_storage()
    results = {"base_key": base_key}

    # Generate and save each responsive WebP size
    for size_name, spec in SIZE_SPECS.items():
        compressed_bytes = resize_and_compress(
            pil_image,
            max_dim=spec["max_dim"],
            quality=spec["quality"]
        )
        variant_key = f"{base_key}_{size_name}.webp"
        saved_key = storage.save(compressed_bytes, variant_key, content_type="image/webp")
        results[size_name] = saved_key

    # Default key stored in model records (medium size by default)
    results["primary_key"] = results["medium"]
    return results


def get_image_url(image_key: str, size: str = "medium") -> str:
    """Returns the URL for a specific image size ('thumb', 'medium', 'large').
    Automatically derives the responsive variant from base or medium keys.
    """
    if not image_key:
        return "/static/images/placeholder_perfume.webp"

    # If it's already an external or static asset
    if image_key.startswith("http://") or image_key.startswith("https://"):
        return image_key

    storage = get_storage()

    # If it's a seed or static image e.g. /static/images/perfume_velvet_oud.webp
    if image_key.startswith("/static/") or image_key.startswith("static/"):
        return image_key if image_key.startswith("/") else f"/{image_key}"

    # Extract base key by stripping _thumb.webp, _medium.webp, _large.webp or .webp
    clean_key = image_key.lstrip("/")
    for s in ("_thumb.webp", "_medium.webp", "_large.webp"):
        if clean_key.endswith(s):
            clean_key = clean_key[:-len(s)]
            break
    else:
        if clean_key.endswith(".webp"):
            clean_key = clean_key[:-5]

    variant_key = f"{clean_key}_{size}.webp"
    return storage.url_for(variant_key)


def get_image_srcset(image_key: str) -> str:
    """Generates standard HTML srcset string for responsive images."""
    if not image_key or image_key.startswith("http://") or image_key.startswith("https://"):
        return ""
    if image_key.startswith("/static/") or image_key.startswith("static/"):
        # For seed static files, return single url
        url = image_key if image_key.startswith("/") else f"/{image_key}"
        return f"{url} 400w, {url} 800w, {url} 1200w"

    thumb_url = get_image_url(image_key, "thumb")
    medium_url = get_image_url(image_key, "medium")
    large_url = get_image_url(image_key, "large")

    return f"{thumb_url} 400w, {medium_url} 800w, {large_url} 1200w"


def delete_image_bundle(image_key: str) -> bool:
    """Cleans up all responsive sizes for an image on delete or replace."""
    if not image_key or image_key.startswith("http") or image_key.startswith("/static/"):
        return False

    clean_key = image_key.lstrip("/")
    for s in ("_thumb.webp", "_medium.webp", "_large.webp"):
        if clean_key.endswith(s):
            clean_key = clean_key[:-len(s)]
            break
    else:
        if clean_key.endswith(".webp"):
            clean_key = clean_key[:-5]

    storage = get_storage()
    success = True
    for size_name in SIZE_SPECS.keys():
        variant_key = f"{clean_key}_{size_name}.webp"
        storage.delete(variant_key)

    # Also delete raw key if stored directly
    storage.delete(image_key)
    return success
