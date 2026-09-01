from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AuditLogView:
    id: str
    action_code: str
    resource_type: str
    resource_id: str | None
    actor_user_id: str | None
    request_id: str
    result: str
    summary_safe: str | None
    occurred_at: datetime
