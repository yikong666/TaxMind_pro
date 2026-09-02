from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from taxmind.modules.conversations.domain import ConversationRecord, MessageRecord
from taxmind.modules.query.application.service import (
    CompleteQueryRunCommand,
    QueryRunCommand,
    QueryRunService,
)
from taxmind.modules.query.domain import QueryRun, QueryRunEvent
from taxmind.modules.risk.domain import RiskRuleDefinition
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

NOW = datetime(2026, 9, 2, tzinfo=UTC)
PRINCIPAL = Principal(
    user_id="user-1",
    org_id="org-1",
    session_id="session-1",
    roles=frozenset(("consultant",)),
    permissions=frozenset(("cases:read", "cases:write")),
)


class _SnapshotResolver:
    async def resolve_active_snapshot_ids(self, org_id: str) -> tuple[str | None, str | None]:
        assert org_id == "org-1"
        return "public-snapshot-1", None


class _Repository:
    def __init__(self) -> None:
        self.conversation = ConversationRecord(
            id="conversation-1",
            org_id="org-1",
            case_id="case-1",
            title="虚构咨询",
            status="active",
            started_by="user-1",
            last_message_at=None,
            summary_version=0,
            created_at=NOW,
            updated_at=NOW,
        )
        self.runs: dict[str, QueryRun] = {}
        self.messages: list[MessageRecord] = []
        self.events: list[QueryRunEvent] = []
        self.audit_actions: list[str] = []

    async def get_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None:
        if conversation_id == self.conversation.id and org_id == self.conversation.org_id:
            return self.conversation
        return None

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
        return len([event for event in self.events if event.run_id == run_id]) + 1

    async def create_event(self, event: QueryRunEvent) -> None:
        self.events.append(event)

    async def list_events(
        self, run_id: str, org_id: str, after_sequence: int
    ) -> list[QueryRunEvent]:
        return [
            event
            for event in self.events
            if event.run_id == run_id and event.sequence_no > after_sequence
        ]

    async def next_sequence(self, conversation_id: str, org_id: str) -> int:
        return len(self.messages) + 1

    async def create_message(self, message: MessageRecord) -> None:
        self.messages.append(message)

    async def touch_conversation(self, conversation_id: str, occurred_at: datetime) -> None:
        self.conversation = replace(
            self.conversation,
            last_message_at=occurred_at,
            updated_at=occurred_at,
        )

    async def create_audit_log(self, **values: object) -> None:
        self.audit_actions.append(str(values["action_code"]))


class _UnitOfWork:
    def __init__(self, repository: _Repository) -> None:
        self.repository = repository
        self.commit_count = 0

    async def __aenter__(self) -> _UnitOfWork:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def commit(self) -> None:
        self.commit_count += 1


def _service(
    repository: _Repository,
    *,
    rules: tuple[RiskRuleDefinition, ...] = (),
) -> tuple[QueryRunService, _UnitOfWork]:
    uow = _UnitOfWork(repository)
    return (
        QueryRunService(
            rules=rules,
            uow_factory=lambda: uow,
            snapshot_resolver=_SnapshotResolver(),
        ),
        uow,
    )


def _command(*, facts: dict[str, object]) -> QueryRunCommand:
    return QueryRunCommand(
        case_id="case-1",
        conversation_id="conversation-1",
        profile_version=1,
        query="这项优惠是否适用",
        facts=facts,
        idempotency_key="query-idempotency-1",
        request_id="request-1",
        occurred_at=NOW,
    )


@pytest.mark.asyncio
async def test_query_run_persists_scope_snapshot_rules_and_request_message() -> None:
    repository = _Repository()
    service, uow = _service(
        repository,
        rules=(
            RiskRuleDefinition(
                rule_version_id="risk-v1",
                severity="high",
                trigger_expression={"gte": {"fact_key": "invoice_amount", "value": 100}},
                missing_fact_policy="manual_review",
                basis_chunk_ids=("chunk-1",),
            ),
        ),
    )

    run = await service.submit(
        _command(
            facts={
                "business_date": date(2026, 8, 31),
                "region_code": "440300",
                "invoice_amount": 120,
            }
        ),
        PRINCIPAL,
    )

    assert run.status == "queued"
    assert run.public_knowledge_snapshot_id == "public-snapshot-1"
    assert run.facts_snapshot["invoice_amount"] == 120
    assert run.rule_version_ids == ("risk-v1",)
    assert run.evidence_ids == ("chunk-1",)
    assert repository.messages[0].role == "user"
    assert repository.messages[0].run_id == run.id
    assert repository.runs[run.id] == run
    assert repository.audit_actions == ["query.run.queued"]
    assert [
        (event.sequence_no, event.event_type, event.payload) for event in repository.events
    ] == [(1, "started", {"status": "queued"})]
    assert uow.commit_count == 1


@pytest.mark.asyncio
async def test_query_run_interrupts_before_queue_when_scope_facts_are_missing() -> None:
    repository = _Repository()
    service, _ = _service(repository)

    run = await service.submit(_command(facts={}), PRINCIPAL)

    assert run.status == "needs_input"
    assert run.retrieval_plan is None
    assert run.follow_up_fact_keys == ("business_date", "region_code")
    assert repository.audit_actions == ["query.run.needs_input"]
    assert repository.events[0].event_type == "needs_input"
    assert repository.events[0].payload["follow_up_fact_keys"] == [
        "business_date",
        "region_code",
    ]


@pytest.mark.asyncio
async def test_final_answer_and_assistant_message_are_persisted_in_one_commit() -> None:
    repository = _Repository()
    service, uow = _service(repository)
    run = await service.submit(
        _command(
            facts={
                "business_date": date(2026, 8, 31),
                "region_code": "440300",
            }
        ),
        PRINCIPAL,
    )

    completed = await service.complete_final_answer(
        CompleteQueryRunCommand(
            run_id=run.id,
            answer_text="依据已发布证据, 当前信息仅支持内部初步判断。",
            citation_ids=("chunk-2",),
            evidence_ids=("chunk-2",),
            gap_codes=("manual_review_required",),
            request_id="request-complete-1",
            occurred_at=NOW,
        ),
        PRINCIPAL,
    )

    assert completed.status == "completed"
    assert completed.final_answer is not None
    assert completed.final_answer.citation_ids == ("chunk-2",)
    assert completed.final_answer.text.startswith("依据已发布证据")
    assistant = repository.messages[-1]
    assert assistant.role == "assistant"
    assert assistant.run_id == run.id
    assert assistant.content_json == {
        "citation_ids": ["chunk-2"],
        "gap_codes": ["manual_review_required"],
    }
    assert "reasoning" not in assistant.content_json
    assert [(event.sequence_no, event.event_type) for event in repository.events] == [
        (1, "started"),
        (2, "delta"),
        (3, "completed"),
    ]
    assert repository.events[1].payload == {
        "message_id": assistant.id,
        "text": assistant.content_text,
        "citation_ids": ["chunk-2"],
    }
    assert "reasoning" not in repository.events[1].payload
    assert repository.audit_actions[-1] == "query.run.completed"
    assert uow.commit_count == 2


@pytest.mark.asyncio
async def test_final_answer_rejects_citation_not_present_in_evidence() -> None:
    repository = _Repository()
    service, uow = _service(repository)
    run = await service.submit(
        _command(
            facts={
                "business_date": date(2026, 8, 31),
                "region_code": "440300",
            }
        ),
        PRINCIPAL,
    )

    with pytest.raises(DomainError, match="引用"):
        await service.complete_final_answer(
            CompleteQueryRunCommand(
                run_id=run.id,
                answer_text="不应保存的回答",
                citation_ids=("unknown-chunk",),
                evidence_ids=("chunk-2",),
                gap_codes=(),
                request_id="request-complete-2",
                occurred_at=NOW,
            ),
            PRINCIPAL,
        )

    assert len(repository.messages) == 1
    assert repository.runs[run.id].status == "queued"
    assert uow.commit_count == 1
