from __future__ import annotations


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, accepted_enrollment_tokens: tuple[str, ...], accepted_analyst_tokens: tuple[str, ...]) -> None:
        self.accepted_enrollment_tokens = set(accepted_enrollment_tokens)
        self.accepted_analyst_tokens = set(accepted_analyst_tokens)

    def authenticate_enrollment_token(self, token: str) -> None:
        if not isinstance(token, str) or token not in self.accepted_enrollment_tokens:
            raise AuthError("invalid enrollment token")
            
    def authenticate_analyst_token(self, token: str) -> None:
        if not isinstance(token, str) or token not in self.accepted_analyst_tokens:
            raise AuthError("invalid analyst token")

