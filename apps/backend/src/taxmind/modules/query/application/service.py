from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Protocol, Self

from taxmind.modules.conversations.domain import ConversationRecord, MessageRecord
from taxmind.modules.query.domain import (
    FinalAnswer,
    QueryRun,
    QueryRunEvent,
    QueryRunEventType,
    QueryRunStatus,
)
from taxmind.modules.retrieval.application.planner import (
    QueryFacts,
    RetrievalPlan,
    build_retrieval_plan,
)
from taxmind.modules.risk.domain import RiskRuleDefinition
from taxmind.modules.risk.evaluator import RuleEvaluation, evaluate_rule
from taxmind.modules.risk.fact_gate import require_scope_facts
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal


class ActiveSnapshotResolver(Protocol):
    async def resolve_active_snapshot_ids(self, org_id: str) -> tuple[str | None, str | None]: ...


class QueryRunsRepository(Protocol):
    async def get_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None: ...

    async def lock_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None: ...

    async def get_run_by_idempotency(
        self, org_id: str, idempotency_key: str
    ) -> QueryRun | None: ...

    async def create_run(self, run: QueryRun) -> None: ...

    async def get_run(self, run_id: str, org_id: str) -> QueryRun | None: ...

    async def lock_run(self, run_id: str, org_id: str) -> QueryRun | None: ...

    async def update_run(self, run: QueryRun) -> None: ...

    async def next_event_sequence(self, run_id: str, org_id: str) -> int: ...

    async def create_event(self, event: QueryRunEvent) -> None: ...

    async def list_events(
        self, run_id: str, org_id: str, after_sequence: int
    ) -> list[QueryRunEvent]: ...

    async def next_sequence(self, conversation_id: str, org_id: str) -> int: ...

    async def create_message(self, message: MessageRecord) -> None: ...

    async def touch_conversation(self, conversation_id: str, occurred_at: datetime) -> None: ...

    async def create_audit_log(self, **values: object) -> None: ...


class QueryRunsUnitOfWork(Protocol):
    @property
    def repository(self) -> QueryRunsRepository | None: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    async def commit(self) -> None: ...


@dataclass(frozen=True, slots=True)
class QueryRunCommand:
    case_id: str
    conversation_id: str
    profile_version: int
    query: str
    facts: dict[str, object]
    idempotency_key: str
    request_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CompleteQueryRunCommand:
    run_id: str
    answer_text: str
    citation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    gap_codes: tuple[str, ...]
    request_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class FailQueryRunCommand:
    run_id: str
    error_code: str
    error_detail_safe: str
    request_id: str
    occurred_at: datetime


class QueryRunService:
    """Persists governed query runs; model execution is supplied by a separate worker."""

    def __init__(
        self,
        *,
        rules: tuple[RiskRuleDefinition, ...],
        uow_factory: Callable[[], QueryRunsUnitOfWork],
        snapshot_resolver: ActiveSnapshotResolver,
    ) -> None:
        self._rules = rules
        self._uow_factory = uow_factory
        self._snapshot_resolver = snapshot_resolver

    async def submit(self, command: QueryRunCommand, principal: Principal) -> QueryRun:
        _require_write(principal)
        query = _normalized_text(command.query, label="查询内容", max_length=4000)
        idempotency_key = _normalized_text(command.idempotency_key, label="幂等键", max_length=100)
        resolver = self._snapshot_resolver
        public_snapshot_id, org_snapshot_id = await resolver.resolve_active_snapshot_ids(
            principal.org_id
        )
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            existing = await repository.get_run_by_idempotency(principal.org_id, idempotency_key)
            if existing is not None:
                return existing
            conversation = await repository.lock_conversation(
                command.conversation_id, principal.org_id
            )
            if (
                conversation is None
                or conversation.case_id != command.case_id
                or conversation.status != "active"
            ):
                raise DomainError(code="RESOURCE_NOT_FOUND", message="会话不存在或不可用于查询")
            run_id = new_id()
            request_message = MessageRecord(
                id=new_id(),
                org_id=principal.org_id,
                conversation_id=conversation.id,
                case_id=command.case_id,
                sequence_no=await repository.next_sequence(conversation.id, principal.org_id),
                role="user",
                content_text=query,
                content_json={},
                run_id=run_id,
                parent_message_id=None,
                visibility="user_visible",
                content_hash=hashlib.sha256(query.encode("utf-8")).hexdigest(),
                redaction_status="not_needed",
                idempotency_key=f"query:{idempotency_key}",
                created_at=command.occurred_at,
            )
            gate = require_scope_facts(
                business_date=_as_date(command.facts.get("business_date")),
                region_code=_as_region(command.facts.get("region_code")),
            )
            plan: RetrievalPlan | None = None
            rule_results: tuple[RuleEvaluation, ...] = ()
            follow_up = gate.missing_fact_keys
            degradation_events: tuple[str, ...] = ()
            if not gate.should_interrupt:
                plan = build_retrieval_plan(
                    query=query,
                    facts=QueryFacts(
                        business_date=_as_date(command.facts.get("business_date")),
                        region_code=_as_region(command.facts.get("region_code")),
                        taxpayer_type=_as_text(command.facts.get("vat_taxpayer_type")),
                    ),
                )
                rule_results = tuple(evaluate_rule(rule, command.facts) for rule in self._rules)
                rule_follow_up = tuple(
                    dict.fromkeys(
                        key for result in rule_results for key in result.missing_fact_keys
                    )
                )
                follow_up = tuple(dict.fromkeys((*plan.missing_facts, *rule_follow_up)))
                degradation_events = ("out_of_scope",) if plan.route_code == "out_of_scope" else ()
            status, error_code, error_detail = _initial_status(
                follow_up=follow_up,
                public_snapshot_id=public_snapshot_id,
            )
            run = QueryRun(
                id=run_id,
                status=status,
                org_id=principal.org_id,
                case_id=command.case_id,
                conversation_id=conversation.id,
                request_message_id=request_message.id,
                profile_version=command.profile_version,
                query_text=query,
                facts_snapshot=dict(command.facts),
                public_knowledge_snapshot_id=public_snapshot_id,
                org_knowledge_snapshot_id=org_snapshot_id,
                retrieval_plan=plan,
                rule_results=rule_results,
                rule_version_ids=tuple(result.rule_version_id for result in rule_results),
                evidence_ids=tuple(
                    dict.fromkeys(
                        evidence_id
                        for result in rule_results
                        for evidence_id in result.basis_chunk_ids
                    )
                ),
                follow_up_fact_keys=follow_up,
                degradation_events=degradation_events,
                model_profile_id=None,
                prompt_bundle_version=None,
                router_version="deterministic-v1",
                retrieval_config_version="baseline-v1",
                idempotency_key=idempotency_key,
                request_id=command.request_id,
                started_at=None,
                completed_at=command.occurred_at if status == "failed" else None,
                error_code=error_code,
                error_detail_safe=error_detail,
                final_answer=None,
                created_at=command.occurred_at,
                updated_at=command.occurred_at,
                audit_resource_id=run_id,
            )
            await repository.create_message(request_message)
            await repository.create_run(run)
            await _record_event(repository, run, command.occurred_at)
            await repository.touch_conversation(conversation.id, command.occurred_at)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code=f"query.run.{status}",
                resource_id=run.id,
                request_id=command.request_id,
                occurred_at=command.occurred_at,
                result=status,
            )
            await uow.commit()
            return run

    async def get(self, run_id: str, principal: Principal) -> QueryRun | None:
        _require_read(principal)
        async with self._uow_factory() as uow:
            return await _repository(uow).get_run(run_id, principal.org_id)

    async def list_events(
        self, run_id: str, *, after_sequence: int, principal: Principal
    ) -> list[QueryRunEvent]:
        _require_read(principal)
        if after_sequence < 0:
            raise DomainError(code="VALIDATION_ERROR", message="事件游标无效")
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            if await repository.get_run(run_id, principal.org_id) is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="查询运行不存在或无权访问")
            return await repository.list_events(run_id, principal.org_id, after_sequence)

    async def mark_running(
        self,
        run_id: str,
        *,
        model_profile_id: str,
        prompt_bundle_version: str,
        request_id: str,
        occurred_at: datetime,
        principal: Principal,
    ) -> QueryRun:
        _require_write(principal)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            run = await _locked_run(repository, run_id, principal.org_id)
            if run.status != "queued":
                raise DomainError(code="RESOURCE_CONFLICT", message="当前运行状态不能开始执行")
            updated = replace(
                run,
                status="running",
                model_profile_id=_normalized_text(
                    model_profile_id, label="模型配置", max_length=100
                ),
                prompt_bundle_version=_normalized_text(
                    prompt_bundle_version, label="提示词版本", max_length=100
                ),
                started_at=occurred_at,
                updated_at=occurred_at,
            )
            await repository.update_run(updated)
            await _record_event(repository, updated, occurred_at)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="query.run.started",
                resource_id=run.id,
                request_id=request_id,
                occurred_at=occurred_at,
                result="running",
            )
            await uow.commit()
            return updated

    async def complete_final_answer(
        self, command: CompleteQueryRunCommand, principal: Principal
    ) -> QueryRun:
        _require_write(principal)
        answer_text = _normalized_text(command.answer_text, label="最终回答", max_length=20000)
        evidence_ids = tuple(dict.fromkeys(command.evidence_ids))
        citation_ids = tuple(dict.fromkeys(command.citation_ids))
        if not set(citation_ids).issubset(evidence_ids):
            raise DomainError(code="CITATION_VALIDATION_FAILED", message="回答引用不在证据清单中")
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            run = await _locked_run(repository, command.run_id, principal.org_id)
            if run.status == "completed" and run.final_answer is not None:
                return run
            if run.status not in {"queued", "running"}:
                raise DomainError(code="RESOURCE_CONFLICT", message="当前运行状态不能保存最终回答")
            if run.public_knowledge_snapshot_id is None:
                raise DomainError(code="KNOWLEDGE_SNAPSHOT_REQUIRED", message="缺少已激活知识快照")
            conversation = await repository.lock_conversation(run.conversation_id, principal.org_id)
            if conversation is None or conversation.status != "active":
                raise DomainError(code="RESOURCE_CONFLICT", message="会话不可写入最终回答")
            message = MessageRecord(
                id=new_id(),
                org_id=principal.org_id,
                conversation_id=run.conversation_id,
                case_id=run.case_id,
                sequence_no=await repository.next_sequence(run.conversation_id, principal.org_id),
                role="assistant",
                content_text=answer_text,
                content_json={
                    "citation_ids": list(citation_ids),
                    "gap_codes": list(dict.fromkeys(command.gap_codes)),
                },
                run_id=run.id,
                parent_message_id=run.request_message_id,
                visibility="user_visible",
                content_hash=hashlib.sha256(answer_text.encode("utf-8")).hexdigest(),
                redaction_status="not_needed",
                idempotency_key=f"run-final:{run.id}",
                created_at=command.occurred_at,
            )
            final_answer = FinalAnswer(
                message_id=message.id,
                text=answer_text,
                citation_ids=citation_ids,
                gap_codes=tuple(dict.fromkeys(command.gap_codes)),
                created_at=command.occurred_at,
            )
            completed = replace(
                run,
                status="completed",
                evidence_ids=evidence_ids,
                completed_at=command.occurred_at,
                error_code=None,
                error_detail_safe=None,
                final_answer=final_answer,
                updated_at=command.occurred_at,
            )
            await repository.create_message(message)
            await repository.update_run(completed)
            await _record_event(
                repository,
                completed,
                command.occurred_at,
                event_type="delta",
                payload={
                    "message_id": message.id,
                    "text": answer_text,
                    "citation_ids": list(citation_ids),
                },
            )
            await _record_event(repository, completed, command.occurred_at)
            await repository.touch_conversation(run.conversation_id, command.occurred_at)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="query.run.completed",
                resource_id=run.id,
                request_id=command.request_id,
                occurred_at=command.occurred_at,
                result="completed",
            )
            await uow.commit()
            return completed

    async def fail(self, command: FailQueryRunCommand, principal: Principal) -> QueryRun:
        _require_write(principal)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            run = await _locked_run(repository, command.run_id, principal.org_id)
            if run.status not in {"queued", "running"}:
                raise DomainError(code="RESOURCE_CONFLICT", message="当前运行状态不能标记失败")
            failed = replace(
                run,
                status="failed",
                error_code=_normalized_text(command.error_code, label="错误码", max_length=100),
                error_detail_safe=_normalized_text(
                    command.error_detail_safe, label="安全错误说明", max_length=1000
                ),
                completed_at=command.occurred_at,
                updated_at=command.occurred_at,
            )
            await repository.update_run(failed)
            await _record_event(repository, failed, command.occurred_at)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="query.run.failed",
                resource_id=run.id,
                request_id=command.request_id,
                occurred_at=command.occurred_at,
                result="failed",
            )
            await uow.commit()
            return failed


def _initial_status(
    *, follow_up: tuple[str, ...], public_snapshot_id: str | None
) -> tuple[QueryRunStatus, str | None, str | None]:
    if follow_up:
        return "needs_input", None, None
    if public_snapshot_id is None:
        return (
            "failed",
            "KNOWLEDGE_SNAPSHOT_UNAVAILABLE",
            "当前没有已激活的公共知识快照, 未启动模型运行。",
        )
    return "queued", None, None


def _repository(uow: QueryRunsUnitOfWork) -> QueryRunsRepository:
    if uow.repository is None:
        raise RuntimeError("unit of work repository is unavailable")
    return uow.repository


async def _locked_run(repository: QueryRunsRepository, run_id: str, org_id: str) -> QueryRun:
    run = await repository.lock_run(run_id, org_id)
    if run is None:
        raise DomainError(code="RESOURCE_NOT_FOUND", message="查询运行不存在或无权访问")
    return run


async def _record_event(
    repository: QueryRunsRepository,
    run: QueryRun,
    occurred_at: datetime,
    *,
    event_type: QueryRunEventType | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    resolved_type = event_type or _status_event_type(run.status)
    event_payload = payload if payload is not None else _status_event_payload(run)
    sequence_no = await repository.next_event_sequence(run.id, run.org_id)
    await repository.create_event(
        QueryRunEvent(
            id=new_id(),
            run_id=run.id,
            sequence_no=sequence_no,
            event_type=resolved_type,
            occurred_at=occurred_at,
            payload=event_payload,
        )
    )


def _status_event_type(status: QueryRunStatus) -> QueryRunEventType:
    if status == "needs_input":
        return "needs_input"
    if status == "completed":
        return "completed"
    if status == "failed":
        return "failed"
    return "started"


def _status_event_payload(run: QueryRun) -> dict[str, object]:
    payload: dict[str, object] = {"status": run.status}
    if run.follow_up_fact_keys:
        payload["follow_up_fact_keys"] = list(run.follow_up_fact_keys)
    if run.error_code is not None:
        payload["error_code"] = run.error_code
    if run.error_detail_safe is not None:
        payload["error_detail_safe"] = run.error_detail_safe
    if run.final_answer is not None:
        payload["message_id"] = run.final_answer.message_id
        payload["citation_ids"] = list(run.final_answer.citation_ids)
        payload["gap_codes"] = list(run.final_answer.gap_codes)
    return payload


def _require_read(principal: Principal) -> None:
    if not principal.has_permission("cases:read"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无事项读取权限")


def _require_write(principal: Principal) -> None:
    if not principal.has_permission("cases:write"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无事项写入权限")


def _normalized_text(value: str, *, label: str, max_length: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise DomainError(code="VALIDATION_ERROR", message=f"{label}不能为空")
    if len(normalized) > max_length:
        raise DomainError(code="VALIDATION_ERROR", message=f"{label}过长")
    return normalized


def _as_date(value: object) -> date | None:
    return value if isinstance(value, date) else None


def _as_region(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _as_text(value: object) -> str | None:
    return value if isinstance(value, str) else None
