from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from taxmind.modules.identity.application.service import IdentityService
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

_bearer = HTTPBearer(auto_error=False)


def identity_service_from(request: Request) -> IdentityService:
    services = cast(dict[str, object], request.app.state.services)
    service = services.get("identity")
    if not isinstance(service, IdentityService):
        raise RuntimeError("identity service is not configured")
    return service


async def current_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise DomainError(code="AUTH_REQUIRED", message="请先登录后再继续")
    return await identity_service_from(request).authenticate_access_token(credentials.credentials)


def require_permission(permission: str) -> Callable[..., object]:
    async def dependency(
        principal: Annotated[Principal, Depends(current_principal)],
    ) -> Principal:
        if not principal.has_permission(permission):
            raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无此操作权限")
        return principal

    return dependency
