from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from taxmind.modules.conversations.domain import ConversationRecord, MessageRecord
from taxmind.modules.query.application.service import QueryRunService
from taxmind.modules.query.domain import QueryRun, QueryRunEvent
from taxmind.modules.risk.domain import RiskRuleDefinition
from taxmind.shared.domain.principal import Principal


class SnapshotResolver:
    async def resolve_active_snapshot_ids(self, org_id: str) -> tuple[str | None, str | None]:
        del org_id
        return "golden-public-snapshot", None


class Repository:
    def __init__(self, *, org_id: str, case_id: str, conversation_id: str, user_id: str) -> None:
        now = datetime(2026, 9, 1, tzinfo=UTC)
        self.conversation = ConversationRecord(
            id=conversation_id,
            org_id=org_id,
            case_id=case_id,
            title="虚构金标准会话",
            status="active",
            started_by=user_id,
            last_message_at=None,
            summary_version=0,
            created_at=now,
            updated_at=now,
        )
        self.runs: dict[str, QueryRun] = {}
        self.events: list[QueryRunEvent] = []
        self.messages: list[MessageRecord] = []
        self.audit_actions: list[str] = []

    async def get_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None:
        return (
            self.conversation
            if conversation_id == self.conversation.id and org_id == self.conversation.org_id
            else None
        )

    async def lock_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None:
        return await self.get_conversation(conversation_id, org_id)

    async def get_run_by_idempotency(self, org_id: str, idempotency_key: str) -> QueryRun | None:
        return next(
            (
                run
                for run in self.runs.values()
                if run.org_id == org_id and run.idempotency_key == idempotency_key
            ),
            None,
        )

    async def create_run(self, run: QueryRun) -> None:
        self.runs[run.id] = run

    async def get_run(self, run_id: str, org_id: str) -> QueryRun | None:
        run = self.runs.get(run_id)
        return run if run is not None and run.org_id == org_id else None

    async def lock_run(self, run_id: str, org_id: str) -> QueryRun | None:
        return await self.get_run(run_id, org_id)

    async def update_run(self, run: QueryRun) -> None:
        self.runs[run.id] = run

    async def next_event_sequence(self, run_id: str, org_id: str) -> int:
        del org_id
        return len([event for event in self.events if event.run_id == run_id]) + 1

    async def create_event(self, event: QueryRunEvent) -> None:
        self.events.append(event)

    async def list_events(
        self, run_id: str, org_id: str, after_sequence: int
    ) -> list[QueryRunEvent]:
        del org_id
        return [
            event
            for event in self.events
            if event.run_id == run_id and event.sequence_no > after_sequence
        ]

    async def next_sequence(self, conversation_id: str, org_id: str) -> int:
        del conversation_id, org_id
        return len(self.messages) + 1

    async def create_message(self, message: MessageRecord) -> None:
        self.messages.append(message)

    async def touch_conversation(self, conversation_id: str, occurred_at: datetime) -> None:
        del conversation_id
        self.conversation = replace(
            self.conversation, last_message_at=occurred_at, updated_at=occurred_at
        )

    async def create_audit_log(self, **values: object) -> None:
        self.audit_actions.append(str(values["action_code"]))


class UnitOfWork:
    def __init__(self, repository: Repository) -> None:
        self.repository: Repository | None = repository

    async def __aenter__(self) -> UnitOfWork:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def commit(self) -> None:
        return None


def make_service(
    *,
    rules: tuple[RiskRuleDefinition, ...],
    org_id: str,
    case_id: str,
    conversation_id: str,
    user_id: str,
) -> tuple[QueryRunService, Principal, Repository]:
    repository = Repository(
        org_id=org_id,
        case_id=case_id,
        conversation_id=conversation_id,
        user_id=user_id,
    )
    service = QueryRunService(
        rules=rules,
        uow_factory=lambda: UnitOfWork(repository),
        snapshot_resolver=SnapshotResolver(),
    )
    principal = Principal(
        user_id=user_id,
        org_id=org_id,
        session_id="golden-session",
        roles=frozenset(("consultant",)),
        permissions=frozenset(("cases:read", "cases:write")),
    )
    return service, principal, repository
