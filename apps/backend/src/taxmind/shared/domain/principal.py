from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated user context that is safe to pass into application services."""

    user_id: str
    org_id: str
    session_id: str
    roles: frozenset[str]
    permissions: frozenset[str]

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions
