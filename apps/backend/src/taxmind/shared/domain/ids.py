from __future__ import annotations

import secrets
import time
import uuid

from taxmind.shared.domain.errors import DomainError


def new_id() -> str:
    """Generate a UUIDv7 string without relying on Python 3.14's uuid.uuid7."""
    timestamp_ms = (time.time_ns() // 1_000_000) & ((1 << 48) - 1)
    random_a = secrets.randbits(12)
    random_b = secrets.randbits(62)
    value = (timestamp_ms << 80) | (0x7 << 76) | (random_a << 64) | (0b10 << 62) | random_b
    return str(uuid.UUID(int=value))


def parse_id(value: str) -> str:
    """Validate and normalize a UUID string."""
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise DomainError(
            code="VALIDATION_FAILED",
            message="资源标识格式无效",
            details={"field": "id"},
        ) from exc
    return str(parsed)
