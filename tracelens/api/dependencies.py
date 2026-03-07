from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from tracelens.config import API_KEY

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Depends(api_key_header)) -> None:
    """Verify API key for write endpoints. Skip if API_KEY not configured."""
    if not API_KEY:
        return
    if not api_key or api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
