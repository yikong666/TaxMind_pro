from __future__ import annotations

import uuid

import pytest

from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id, parse_id


def test_new_id_returns_uuid7() -> None:
    generated = uuid.UUID(new_id())

    assert generated.version == 7
    assert generated.variant == uuid.RFC_4122


def test_parse_id_normalizes_uuid() -> None:
    value = "01900000-0000-7000-8000-000000000001"

    assert parse_id(value.upper()) == value


def test_parse_id_rejects_invalid_value() -> None:
    with pytest.raises(DomainError) as error:
        parse_id("not-an-id")

    assert error.value.code == "VALIDATION_FAILED"