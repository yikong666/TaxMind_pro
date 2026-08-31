from __future__ import annotations

from typing import Protocol


class MilvusAliasClient(Protocol):
    def alter_alias(self, collection_name: str, alias: str) -> None: ...


def activate_policy_alias(client: MilvusAliasClient, *, collection_name: str, alias: str) -> None:
    if not collection_name.startswith("policy_chunks_"):
        raise ValueError("policy alias target must be a versioned policy collection")
    if alias != "policy_chunks_current":
        raise ValueError("only the configured policy alias may be switched")
    client.alter_alias(collection_name, alias)


def activate_policy_alias_after_smoke_check(
    client: MilvusAliasClient,
    *,
    collection_name: str,
    alias: str,
    smoke_check_passed: bool,
) -> None:
    if not smoke_check_passed:
        raise ValueError("projection smoke check must pass before alias switch")
    activate_policy_alias(client, collection_name=collection_name, alias=alias)
