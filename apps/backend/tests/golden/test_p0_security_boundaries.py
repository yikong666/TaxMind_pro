from __future__ import annotations

from taxmind.modules.identity.domain import permissions_for_role


def test_p0_golden_audit_read_is_separated_from_feedback_management() -> None:
    auditor_permissions = permissions_for_role("auditor")
    consultant_permissions = permissions_for_role("consultant")
    knowledge_admin_permissions = permissions_for_role("knowledge_admin")

    assert "audit:read" in auditor_permissions
    assert "feedback:manage" not in auditor_permissions
    assert "feedback:write" in consultant_permissions
    assert "audit:read" not in consultant_permissions
    assert "feedback:manage" in knowledge_admin_permissions
