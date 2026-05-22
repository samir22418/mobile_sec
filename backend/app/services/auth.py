from __future__ import annotations


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, accepted_tokens: tuple[str, ...]) -> None:
        self.accepted_tokens = set(accepted_tokens)

    def authenticate_payload(self, payload: dict) -> None:
        token = payload.get("enrollment_token")
        if not isinstance(token, str) or token not in self.accepted_tokens:
            raise AuthError("invalid enrollment token")

