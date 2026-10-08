import re
from urllib.parse import urlsplit


def get_safe_redirect_url(target: str | None, default_url: str = "/") -> str:
    """Validates that a redirect target is strictly a safe internal relative path.

    Defends against:
    - Open redirects to external domains (e.g. https://evil.example)
    - Protocol-relative URLs (e.g. //evil.example)
    - Backslash obfuscation (e.g. /\\evil.example)
    - JavaScript / Data schemes (e.g. javascript:alert(1))
    - Control character / CRLF injection (e.g. \\r\\n)
    """
    if not target or not isinstance(target, str):
        return default_url

    clean_target = target.strip()
    if not clean_target:
        return default_url

    # Check for CRLF / control chars
    if any(c in clean_target for c in ("\r", "\n", "\t", "\x00")):
        return default_url

    # Must start with exactly one forward slash, not // or /\
    if not clean_target.startswith("/") or clean_target.startswith("//") or clean_target.startswith("/\\"):
        return default_url

    try:
        parsed = urlsplit(clean_target)
    except Exception:
        return default_url

    # Reject any URL with a scheme or network location (external host)
    if parsed.scheme or parsed.netloc:
        return default_url

    # Disallow pseudo-schemes in path
    lower_path = parsed.path.lower()
    if "javascript:" in lower_path or "data:" in lower_path or "vbscript:" in lower_path:
        return default_url

    # Reassemble path + query safely
    safe_path = parsed.path
    if parsed.query:
        # Sanitize query parameters: reject if containing raw HTML characters or suspicious constructs
        if any(bad in parsed.query for bad in ("<", ">", '"', "'", ";", "--")):
            return safe_path
        safe_path = f"{safe_path}?{parsed.query}"

    return safe_path
