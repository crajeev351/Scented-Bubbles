import re
import posixpath
from urllib.parse import urlsplit, unquote
from pathlib import Path


# Explicit allowlist of permissible internal application route prefixes for redirects
ALLOWED_REDIRECT_PREFIXES = (
    "/admin",
    "/account",
    "/checkout",
    "/cart",
    "/orders",
    "/products",
    "/combos",
    "/categories",
    "/about",
    "/contact",
    "/policies",
)


def get_safe_redirect_url(target: str | None, default_url: str = "/", default: str | None = None) -> str:
    """Validates that a redirect target is strictly a safe, internal, canonical path.

    Defends comprehensively against:
    - Path Traversal (e.g. /../../etc/passwd, %2e%2e%2f, ..\\..\\win.ini)
    - Open redirects to external domains (e.g. https://evil.example)
    - Protocol-relative URLs (e.g. //evil.example)
    - Backslash obfuscation (e.g. /\\evil.example)
    - JavaScript / Data schemes (e.g. javascript:alert(1))
    - Control character / CRLF injection (e.g. \\r\\n)
    """
    if default is not None:
        default_url = default

    if not target or not isinstance(target, str):
        return default_url


    clean_target = target.strip()
    if not clean_target:
        return default_url

    # Check for CRLF / control chars / null bytes
    if any(c in clean_target for c in ("\r", "\n", "\t", "\x00")):
        return default_url

    # Check for encoded or raw directory traversal tokens
    unquoted = unquote(unquote(clean_target))
    if ".." in unquoted or "\\ " in unquoted or "\\" in clean_target:
        return default_url

    # Must start with exactly one forward slash, not // or /\
    if not clean_target.startswith("/") or clean_target.startswith("//") or clean_target.startswith("/\\"):
        return default_url

    try:
        parsed = urlsplit(clean_target)
    except Exception:
        return default_url

    # Reject any URL with an external scheme or network location
    if parsed.scheme or parsed.netloc:
        return default_url

    # Disallow pseudo-schemes in path
    lower_path = parsed.path.lower()
    if any(ps in lower_path for ps in ("javascript:", "data:", "vbscript:", "file:", "blob:")):
        return default_url

    # Canonicalize and normalize path
    norm_path = posixpath.normpath(parsed.path)
    if not norm_path.startswith("/") or norm_path.startswith("//") or ".." in norm_path:
        return default_url

    # Enforce strict route prefix allowlist
    if norm_path != "/" and not norm_path.startswith(ALLOWED_REDIRECT_PREFIXES):
        return default_url

    # Reassemble path + query safely
    safe_path = norm_path
    if parsed.query:
        unquoted_query = unquote(parsed.query)
        # Disallow path traversal, script constructs, or SQL meta-characters in query string
        if any(bad in unquoted_query for bad in ("..", "<", ">", '"', "'", ";", "--", "\x00")):
            return safe_path
        safe_path = f"{safe_path}?{parsed.query}"

    return safe_path


def validate_canonical_storage_path(base_dir: Path, relative_key: str) -> Path:
    """Resolves and validates that a relative key/path remains strictly inside base_dir.
    Raises ValueError on any path traversal attempt or absolute path.
    """
    if not relative_key or not isinstance(relative_key, str):
        raise ValueError("Storage key must be a non-empty string.")

    unquoted_key = unquote(unquote(relative_key)).strip()
    if ".." in unquoted_key or "\x00" in unquoted_key or "\\" in unquoted_key:
        raise ValueError(f"Path traversal characters detected in key: {relative_key}")

    # Reject absolute paths (POSIX / or Windows C:\)
    if unquoted_key.startswith("/") or unquoted_key.startswith("\\") or Path(unquoted_key).is_absolute() or bool(re.match(r"^[a-zA-Z]:", unquoted_key)):
        raise ValueError(f"Absolute paths not permitted in storage key: {relative_key}")

    resolved_base = base_dir.resolve()
    target = (resolved_base / unquoted_key).resolve()

    # Enforce that resolved canonical path is strictly inside base_dir
    try:
        target.relative_to(resolved_base)
    except ValueError:
        raise ValueError(f"Path traversal detected: {relative_key} escapes base directory.")

    return target

