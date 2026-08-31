from __future__ import annotations

import pytest

from taxmind.infrastructure.projections.milvus_alias import (
    activate_policy_alias,
    activate_policy_alias_after_smoke_check,
)


class _Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def alter_alias(self, collection_name: str, alias: str) -> None:
        self.calls.append((collection_name, alias))


def test_policy_alias_switches_only_to_a_versioned_collection() -> None:
    client = _Client()

    activate_policy_alias(
        client,
        collection_name="policy_chunks_initial",
        alias="policy_chunks_current",
    )

    assert client.calls == [("policy_chunks_initial", "policy_chunks_current")]


def test_policy_alias_is_not_switched_when_smoke_check_failed() -> None:
    client = _Client()

    with pytest.raises(ValueError, match="smoke"):
        activate_policy_alias_after_smoke_check(
            client,
            collection_name="policy_chunks_initial",
            alias="policy_chunks_current",
            smoke_check_passed=False,
        )

    assert client.calls == []
