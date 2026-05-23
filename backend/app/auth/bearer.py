from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.services.enrollment_tokens import EnrollmentTokenService
from app.services.auth import AuthError, AuthService

bearer_scheme = HTTPBearer()

def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service

def verify_enrollment_token(
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
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> str:
    try:
        auth_service.authenticate_analyst_token(credentials.credentials)
        return credentials.credentials
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": str(e)},
        )
