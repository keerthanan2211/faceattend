import hmac

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_admin(x_admin_key: str = Header(default="")) -> None:
    """Admin endpoints need the X-Admin-Key header. Compared in constant time to avoid timing attacks."""
    expected = get_settings().admin_api_key
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ADMIN_API_KEY is not configured on the server")
    if not hmac.compare_digest(x_admin_key.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid admin key")
