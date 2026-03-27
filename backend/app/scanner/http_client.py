import httpx

from app.config import settings


def create_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.scanner_timeout, connect=5.0),
        follow_redirects=True,
        max_redirects=5,
        headers={
            "User-Agent": settings.scanner_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
