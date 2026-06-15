from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session


def get_session(request: Request) -> Iterator[Session]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def require_console_key(request: Request) -> None:
    """Enforce API-key authentication on analyst/console endpoints.

    Reads X-Aegis-Api-Key from the request header and compares it to the
    configured console_api_key.  When console_api_key is None (AEGIS_ENV=dev
    with no key configured) this dependency is a transparent no-op so local
    development requires no extra setup.
    """
    api_key: str | None = request.app.state.settings.console_api_key
    if api_key is None:
        return
    provided = request.headers.get("X-Aegis-Api-Key")
    if not provided or provided != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "valid X-Aegis-Api-Key header required"},
        )

