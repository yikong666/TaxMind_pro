from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from taxmind.bootstrap.settings import Settings
from taxmind.modules.identity.domain import permissions_for_role
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

logger = logging.getLogger("taxmind.identity")


class Argon2PasswordService:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (InvalidHashError, VerifyMismatchError):
            return False


class JwtTokenService:
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret.get_secret_value()
        self._algorithm = settings.jwt_algorithm
        self._issuer = settings.jwt_issuer
        self._ttl = timedelta(minutes=settings.access_token_ttl_minutes)

    @property
    def expires_in_seconds(self) -> int:
        return int(self._ttl.total_seconds())

    def issue(self, principal: Principal, *, now: datetime | None = None) -> str:
        issued_at = now or datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": principal.user_id,
            "org_id": principal.org_id,
            "sid": principal.session_id,
            "roles": sorted(principal.roles),
            "iat": issued_at,
            "exp": issued_at + self._ttl,
            "iss": self._issuer,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify(self, raw_token: str) -> Principal:
        try:
            payload = jwt.decode(
                raw_token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                options={"require": ["sub", "org_id", "sid", "roles", "exp", "iat"]},
            )
            roles = payload["roles"]
            if not isinstance(roles, list) or len(roles) != 1 or not isinstance(roles[0], str):
                raise ValueError("invalid role claim")
            role_code = roles[0]
            return Principal(
                user_id=str(payload["sub"]),
                org_id=str(payload["org_id"]),
                session_id=str(payload["sid"]),
                roles=frozenset({role_code}),
                permissions=permissions_for_role(role_code),
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError, DomainError) as exc:
            logger.warning(
                f"access token decode rejected: {type(exc).__name__}",
                extra={
                    "event": "auth.access_token.decode_rejected",
                    "error_code": "AUTH_TOKEN_DECODE_REJECTED",
                },
            )
            raise DomainError(code="AUTH_REQUIRED", message="登录状态无效或已过期") from exc
