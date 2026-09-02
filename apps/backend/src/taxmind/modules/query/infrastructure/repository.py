from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.audit.infrastructure.models import AuditLogModel
from taxmind.modules.conversations.domain import ConversationRecord, MessageRecord
from taxmind.modules.conversations.infrastructure.models import MessageModel
from taxmind.modules.conversations.infrastructure.repository import (
    SqlAlchemyConversationsRepository,
)
from taxmind.modules.query.domain import (
    FinalAnswer,
    QueryRun,
    QueryRunEvent,
    QueryRunEventType,
    QueryRunStatus,
)
from taxmind.modules.query.infrastructure.models import AnalysisRunEventModel, AnalysisRunModel
from taxmind.modules.retrieval.application.planner import (
    GraphExpansionType,
    RetrievalPlan,
    RouteCode,
)
from taxmind.modules.risk.domain import Severity
from taxmind.modules.risk.evaluator import RuleEvaluation, RuleOutcomeStatus


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class SqlAlchemyQueryRunsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._conversations = SqlAlchemyConversationsRepository(session)

    async def get_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None:
        return await self._conversations.get_conversation(conversation_id, org_id)

    async def lock_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None:
        return await self._conversations.lock_conversation(conversation_id, org_id)

    async def get_run_by_idempotency(self, org_id: str, idempotency_key: str) -> QueryRun | None:
        model = await self._session.scalar(
            select(AnalysisRunModel).where(
                AnalysisRunModel.org_id == org_id,
                AnalysisRunModel.idempotency_key == idempotency_key,
            )
        )
        return await self._run_record(model) if model else None

    async def create_run(self, run: QueryRun) -> None:
        self._session.add(
            AnalysisRunModel(
                id=run.id,
                org_id=run.org_id,
                case_id=run.case_id,
                conversation_id=run.conversation_id,
                request_message_id=run.request_message_id,
                status=run.status,
                profile_version=run.profile_version,
                query_text=run.query_text,
                facts_snapshot_json=_json_safe_dict(run.facts_snapshot),
                public_knowledge_snapshot_id=run.public_knowledge_snapshot_id,
                org_knowledge_snapshot_id=run.org_knowledge_snapshot_id,
                retrieval_plan_json=_plan_json(run.retrieval_plan),
                rule_results_json=[_rule_json(item) for item in run.rule_results],
                rule_version_ids_json=list(run.rule_version_ids),
                evidence_ids_json=list(run.evidence_ids),
                follow_up_fact_keys_json=list(run.follow_up_fact_keys),
                degradation_events_json=list(run.degradation_events),
                model_profile_id=run.model_profile_id,
                prompt_bundle_version=run.prompt_bundle_version,
                router_version=run.router_version,
                retrieval_config_version=run.retrieval_config_version,
                idempotency_key=run.idempotency_key,
                request_id=run.request_id,
                started_at=run.started_at,
                completed_at=run.completed_at,
                error_code=run.error_code,
                error_detail_safe=run.error_detail_safe,
                final_answer_message_id=(
                    run.final_answer.message_id if run.final_answer is not None else None
                ),
                created_at=run.created_at,
                updated_at=run.updated_at,
            )
        )

    async def get_run(self, run_id: str, org_id: str) -> QueryRun | None:
        model = await self._session.scalar(
            select(AnalysisRunModel).where(
                AnalysisRunModel.id == run_id,
                AnalysisRunModel.org_id == org_id,
            )
        )
        return await self._run_record(model) if model else None

    async def lock_run(self, run_id: str, org_id: str) -> QueryRun | None:
        model = await self._session.scalar(
            select(AnalysisRunModel)
            .where(
                AnalysisRunModel.id == run_id,
                AnalysisRunModel.org_id == org_id,
            )
            .with_for_update()
        )
        return await self._run_record(model) if model else None

    async def update_run(self, run: QueryRun) -> None:
        await self._session.execute(
            update(AnalysisRunModel)
            .where(
                AnalysisRunModel.id == run.id,
                AnalysisRunModel.org_id == run.org_id,
            )
            .values(
                status=run.status,
                evidence_ids_json=list(run.evidence_ids),
                model_profile_id=run.model_profile_id,
                prompt_bundle_version=run.prompt_bundle_version,
                started_at=run.started_at,
                completed_at=run.completed_at,
                error_code=run.error_code,
                error_detail_safe=run.error_detail_safe,
                final_answer_message_id=(
                    run.final_answer.message_id if run.final_answer is not None else None
                ),
                updated_at=run.updated_at,
            )
        )

    async def next_event_sequence(self, run_id: str, org_id: str) -> int:
        run_exists = await self._session.scalar(
            select(AnalysisRunModel.id).where(
                AnalysisRunModel.id == run_id,
                AnalysisRunModel.org_id == org_id,
            )
        )
        if run_exists is None:
            raise RuntimeError("query run does not exist")
        current = await self._session.scalar(
            select(func.max(AnalysisRunEventModel.sequence_no)).where(
                AnalysisRunEventModel.run_id == run_id
            )
        )
        return int(current or 0) + 1

    async def create_event(self, event: QueryRunEvent) -> None:
        self._session.add(
            AnalysisRunEventModel(
                id=event.id,
                run_id=event.run_id,
                sequence_no=event.sequence_no,
                event_type=event.event_type,
                payload_json=_json_safe_dict(event.payload),
                occurred_at=event.occurred_at,
            )
        )

    async def list_events(
        self, run_id: str, org_id: str, after_sequence: int
    ) -> list[QueryRunEvent]:
        rows = (
            await self._session.scalars(
                select(AnalysisRunEventModel)
                .join(AnalysisRunModel, AnalysisRunModel.id == AnalysisRunEventModel.run_id)
                .where(
                    AnalysisRunEventModel.run_id == run_id,
                    AnalysisRunModel.org_id == org_id,
                    AnalysisRunEventModel.sequence_no > after_sequence,
                )
                .order_by(AnalysisRunEventModel.sequence_no)
            )
        ).all()
        return [
            QueryRunEvent(
                id=row.id,
                run_id=row.run_id,
                sequence_no=row.sequence_no,
                event_type=cast(QueryRunEventType, row.event_type),
                occurred_at=_as_utc(row.occurred_at),
                payload=dict(row.payload_json),
            )
            for row in rows
        ]

    async def next_sequence(self, conversation_id: str, org_id: str) -> int:
        return await self._conversations.next_sequence(conversation_id, org_id)

    async def create_message(self, message: MessageRecord) -> None:
        await self._conversations.create_message(message)

    async def touch_conversation(self, conversation_id: str, occurred_at: datetime) -> None:
        await self._conversations.touch_conversation(conversation_id, occurred_at)

    async def create_audit_log(self, **values: object) -> None:
        self._session.add(
            AuditLogModel(
                org_id=cast(str, values["org_id"]),
                actor_user_id=cast(str, values["actor_user_id"]),
                action_code=cast(str, values["action_code"]),
                resource_type="query_run",
                resource_id=cast(str, values["resource_id"]),
                request_id=cast(str, values["request_id"]),
                result=cast(str, values["result"]),
                occurred_at=cast(datetime, values["occurred_at"]),
            )
        )

    async def _run_record(self, model: AnalysisRunModel) -> QueryRun:
        final_answer: FinalAnswer | None = None
        if model.final_answer_message_id is not None:
            message = await self._session.scalar(
                select(MessageModel).where(
                    MessageModel.id == model.final_answer_message_id,
                    MessageModel.org_id == model.org_id,
                    MessageModel.run_id == model.id,
                    MessageModel.role == "assistant",
                )
            )
            if message is not None:
                final_answer = FinalAnswer(
                    message_id=message.id,
                    text=message.content_text,
                    citation_ids=_string_tuple(message.content_json.get("citation_ids")),
                    gap_codes=_string_tuple(message.content_json.get("gap_codes")),
                    created_at=_as_utc(message.created_at),
                )
        return QueryRun(
            id=model.id,
            status=cast(QueryRunStatus, model.status),
            org_id=model.org_id,
            case_id=model.case_id,
            conversation_id=model.conversation_id,
            request_message_id=model.request_message_id,
            profile_version=model.profile_version,
            query_text=model.query_text,
            facts_snapshot=dict(model.facts_snapshot_json),
            public_knowledge_snapshot_id=model.public_knowledge_snapshot_id,
            org_knowledge_snapshot_id=model.org_knowledge_snapshot_id,
            retrieval_plan=_plan(model.retrieval_plan_json),
            rule_results=tuple(_rule(item) for item in model.rule_results_json),
            rule_version_ids=tuple(model.rule_version_ids_json),
            evidence_ids=tuple(model.evidence_ids_json),
            follow_up_fact_keys=tuple(model.follow_up_fact_keys_json),
            degradation_events=tuple(model.degradation_events_json),
            model_profile_id=model.model_profile_id,
            prompt_bundle_version=model.prompt_bundle_version,
            router_version=model.router_version,
            retrieval_config_version=model.retrieval_config_version,
            idempotency_key=model.idempotency_key,
            request_id=model.request_id,
            started_at=_as_utc(model.started_at) if model.started_at else None,
            completed_at=_as_utc(model.completed_at) if model.completed_at else None,
            error_code=model.error_code,
            error_detail_safe=model.error_detail_safe,
            final_answer=final_answer,
            created_at=_as_utc(model.created_at),
            updated_at=_as_utc(model.updated_at),
            audit_resource_id=model.id,
        )


def _plan_json(plan: RetrievalPlan | None) -> dict[str, object] | None:
    if plan is None:
        return None
    return {
        "route_code": plan.route_code,
        "use_mysql_exact": plan.use_mysql_exact,
        "use_milvus_semantic": plan.use_milvus_semantic,
        "graph_expansion_type": plan.graph_expansion_type,
        "should_interrupt": plan.should_interrupt,
        "missing_facts": list(plan.missing_facts),
    }


def _plan(data: dict[str, object] | None) -> RetrievalPlan | None:
    if data is None:
        return None
    return RetrievalPlan(
        route_code=cast(RouteCode, data["route_code"]),
        use_mysql_exact=bool(data["use_mysql_exact"]),
        use_milvus_semantic=bool(data["use_milvus_semantic"]),
        graph_expansion_type=cast(GraphExpansionType | None, data.get("graph_expansion_type")),
        should_interrupt=bool(data["should_interrupt"]),
        missing_facts=list(_string_tuple(data.get("missing_facts"))),
    )


def _rule_json(result: RuleEvaluation) -> dict[str, object]:
    return {
        "rule_version_id": result.rule_version_id,
        "status": result.status,
        "severity": result.severity,
        "missing_fact_keys": list(result.missing_fact_keys),
        "basis_chunk_ids": list(result.basis_chunk_ids),
    }


def _rule(data: dict[str, object]) -> RuleEvaluation:
    return RuleEvaluation(
        rule_version_id=cast(str, data["rule_version_id"]),
        status=cast(RuleOutcomeStatus, data["status"]),
        severity=cast(Severity | None, data.get("severity")),
        missing_fact_keys=_string_tuple(data.get("missing_fact_keys")),
        basis_chunk_ids=_string_tuple(data.get("basis_chunk_ids")),
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _json_safe_dict(value: dict[str, object]) -> dict[str, object]:
    return {key: _json_safe(item) for key, item in value.items()}


def _json_safe(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
