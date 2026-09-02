from __future__ import annotations

import pytest

from taxmind.bootstrap.settings import Settings
from taxmind.modules.identity.domain import permissions_for_role
from taxmind.modules.identity.infrastructure.security import Argon2PasswordService, JwtTokenService
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal


def _principal() -> Principal:
    return Principal(
        user_id="018f4cc1-7852-7d5d-8c1c-dbd404e8a101",
        org_id="018f4cc1-7852-7d5d-8c1c-dbd404e8a102",
        session_id="018f4cc1-7852-7d5d-8c1c-dbd404e8a103",
        roles=frozenset({"org_admin"}),
        permissions=permissions_for_role("org_admin"),
    )


def test_argon2_password_service_never_accepts_wrong_password() -> None:
    passwords = Argon2PasswordService()
    example_password = "development-password-123"  # noqa: S105 - test fixture only
    password_hash = passwords.hash(example_password)

    assert password_hash != example_password
    assert passwords.verify(password_hash, example_password)
    assert not passwords.verify(password_hash, "incorrect-password-123")


def test_jwt_round_trip_preserves_tenant_bound_principal() -> None:
    tokens = JwtTokenService(Settings(app_env="test"))

    restored = tokens.verify(tokens.issue(_principal()))

    assert restored.user_id == _principal().user_id
    assert restored.org_id == _principal().org_id
    assert restored.has_permission("members:write")


def test_knowledge_admin_permissions_remain_separate_from_org_administration() -> None:
    permissions = permissions_for_role("knowledge_admin")

    assert "knowledge:write" in permissions
    assert "members:write" not in permissions


def test_jwt_rejects_invalid_token_without_claim_details() -> None:
    tokens = JwtTokenService(Settings(app_env="test"))

    with pytest.raises(DomainError) as error:
        tokens.verify("not-a-jwt")

    assert error.value.code == "AUTH_REQUIRED"
    assert "claim" not in error.value.message.lower()
