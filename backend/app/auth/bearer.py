from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.services.auth import AuthError, AuthService
from app.services.enrollment_tokens import EnrollmentTokenService

bearer_scheme = HTTPBearer()


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def verify_enrollment_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    session: Annotated[Session, Depends(get_session)],
) -> str:
    token = credentials.credentials
    if EnrollmentTokenService().authenticate(session, token):
        return token
    try:
        auth_service.authenticate_enrollment_token(token)
        return token
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": str(e)},
        )


def verify_analyst_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> str:
    limiter = getattr(request.app.state, "auth_rate_limiter", None)
    if limiter is not None:
        ip = _client_ip(request)
        if not limiter.allow(f"analyst:{ip}"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "rate_limited", "message": "Too many auth attempts. Try again later."},
            )
    try:
        auth_service.authenticate_analyst_token(credentials.credentials)
        return credentials.credentials
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": str(e)},
        )
